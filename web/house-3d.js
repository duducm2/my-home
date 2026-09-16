import * as THREE from "three";
import { OrbitControls } from "/vendor/three/OrbitControls.js";
import { TransformControls } from "/vendor/three/TransformControls.js";
import { GLTFLoader } from "/vendor/three/GLTFLoader.js";

let activeViewer = null;
let activeFingerprint = "";

const ASSET_CATALOG = {
  sofa: {
    label: "Sofá",
    group: "Sala",
    width: 2.0,
    depth: 0.85,
    height: 0.78,
    color: "#8f6f61",
    modelUrl: "/assets/models/sofa.glb",
    previewUrl: "/assets/models/previews/sofa.png",
  },
  bed: {
    label: "Cama de casal",
    group: "Quarto",
    width: 1.4,
    depth: 1.9,
    height: 0.6,
    color: "#a7b8cc",
    modelUrl: "/assets/models/bed.glb",
    previewUrl: "/assets/models/previews/bed.png",
  },
  table: {
    label: "Mesa de jantar",
    group: "Sala",
    width: 1.4,
    depth: 0.8,
    height: 0.76,
    color: "#8b6542",
    modelUrl: "/assets/models/table.glb",
    previewUrl: "/assets/models/previews/table.png",
  },
  chair: {
    label: "Cadeira",
    group: "Sala",
    width: 0.48,
    depth: 0.48,
    height: 0.9,
    color: "#9a7655",
    modelUrl: "/assets/models/chair.glb",
    previewUrl: "/assets/models/previews/chair.png",
  },
  wardrobe: {
    label: "Guarda-roupa",
    group: "Quarto",
    width: 1.6,
    depth: 0.58,
    height: 2.1,
    color: "#b7a58c",
    modelUrl: "/assets/models/wardrobe.glb",
    previewUrl: "/assets/models/previews/wardrobe.png",
  },
  refrigerator: {
    label: "Geladeira",
    group: "Cozinha e serviço",
    width: 0.72,
    depth: 0.7,
    height: 1.85,
    color: "#d7dde0",
    modelUrl: "/assets/models/refrigerator.glb",
    previewUrl: "/assets/models/previews/refrigerator.jpg",
  },
  stove: {
    label: "Fogão",
    group: "Cozinha e serviço",
    width: 0.62,
    depth: 0.64,
    height: 0.9,
    color: "#646b70",
    modelUrl: "/assets/models/stove.glb",
    previewUrl: "/assets/models/previews/stove.png",
  },
  plant: {
    label: "Planta em vaso",
    group: "Decoração",
    width: 0.5,
    depth: 0.5,
    height: 1.1,
    color: "#4f8c58",
    modelUrl: "/assets/models/plant.glb",
    previewUrl: "/assets/models/previews/plant.png",
  },
  tree: {
    label: "Árvore",
    group: "Exterior",
    width: 3.2,
    depth: 3.2,
    height: 5.0,
    color: "#477a4f",
    modelUrl: "/assets/models/tree.glb",
    previewUrl: "/assets/models/previews/tree.png",
  },
  box: {
    label: "Caixa",
    group: "Utilitários",
    width: 0.6,
    depth: 0.6,
    height: 0.6,
    color: "#a87945",
  },
};

const assetLoader = new GLTFLoader();
const assetModelCache = new Map();

function loadAssetTemplate(definition) {
  if (!definition?.modelUrl) return Promise.resolve(null);
  if (!assetModelCache.has(definition.modelUrl)) {
    assetModelCache.set(
      definition.modelUrl,
      assetLoader.loadAsync(definition.modelUrl).then((gltf) => gltf.scene),
    );
  }
  return assetModelCache.get(definition.modelUrl);
}

const byId = (id) => document.getElementById(id);

function createLabelTexture(text, color = "#f4d03f") {
  const canvas = document.createElement("canvas");
  canvas.width = 512;
  canvas.height = 128;
  const context = canvas.getContext("2d");
  context.clearRect(0, 0, canvas.width, canvas.height);
  context.fillStyle = "rgba(10, 10, 10, .82)";
  context.beginPath();
  context.roundRect(8, 18, 496, 92, 16);
  context.fill();
  context.strokeStyle = color;
  context.lineWidth = 3;
  context.stroke();
  context.fillStyle = "#f4f4f4";
  context.font = "700 31px Segoe UI, sans-serif";
  context.textAlign = "center";
  context.textBaseline = "middle";
  context.fillText(String(text).slice(0, 28), 256, 64, 470);
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.minFilter = THREE.LinearFilter;
  return texture;
}

function disposeMaterial(material) {
  if (!material) return;
  const materials = Array.isArray(material) ? material : [material];
  for (const item of materials) {
    for (const value of Object.values(item)) {
      if (value && value.isTexture) value.dispose();
    }
    item.dispose();
  }
}

class HouseViewer {
  constructor(model) {
    this.model = model;
    this.host = byId("house-3d-canvas");
    this.status = byId("house-3d-status");
    this.detail = byId("house-3d-room-detail");
    this.legend = byId("house-3d-legend");
    this.toolbar = byId("house-3d-toolbar");
    this.roomMeshes = [];
    this.wallMeshes = [];
    this.labelSprites = [];
    this.editorTargets = [];
    this.targetParts = new Map();
    this.placedAssetGroups = [];
    this.editorEnabled = false;
    this.selectedTarget = null;
    this.placementType = "";
    this.layoutOverrides = structuredClone(model.layout_overrides || {});
    this.placedAssets = structuredClone(model.placed_assets || []);
    this.renderPending = false;
    this.pointerStart = null;
    this.selectedFloor = null;
    this.roofVisible = false;
    this.labelsVisible = true;
    this.wallsTransparent = false;
    this.disposed = false;

    if (!this.host) throw new Error("Área do modelo 3D não encontrada.");
    this.init();
  }

  setStatus(text, kind = "") {
    if (!this.status) return;
    this.status.textContent = text;
    this.status.classList.toggle("err", kind === "err");
    this.status.classList.toggle("ok", kind === "ok");
  }

  init() {
    this.host.replaceChildren();
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color("#0d0f10");
    this.scene.fog = new THREE.Fog("#0d0f10", 32, 58);

    this.camera = new THREE.PerspectiveCamera(43, 1, 0.1, 120);
    this.renderer = new THREE.WebGLRenderer({
      antialias: true,
      alpha: false,
      preserveDrawingBuffer: true,
    });
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.05;
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    this.renderer.domElement.setAttribute(
      "aria-label",
      "Modelo 3D interativo da casa",
    );
    this.renderer.domElement.setAttribute("role", "img");
    this.host.appendChild(this.renderer.domElement);

    this.controls = new OrbitControls(this.camera, this.renderer.domElement);
    this.controls.enableDamping = false;
    this.controls.enablePan = true;
    this.controls.screenSpacePanning = false;
    this.controls.minDistance = 5;
    this.controls.maxDistance = 52;
    this.controls.maxPolarAngle = Math.PI / 2.03;
    this.controls.addEventListener("change", () => this.requestRender());

    this.raycaster = new THREE.Raycaster();
    this.pointer = new THREE.Vector2();
    this.sceneRoot = new THREE.Group();
    this.scene.add(this.sceneRoot);

    this.buildLighting();
    this.buildModel();
    this.buildEditor();
    this.buildLegend();
    this.bindInteractions();
    this.resizeObserver = new ResizeObserver(() => this.resize());
    this.resizeObserver.observe(this.host);
    this.setPerspective();
    this.resize();
    this.setStatus(
      "Modelo pronto — arraste para girar, role para aproximar.",
      "ok",
    );
  }

  buildLighting() {
    const hemisphere = new THREE.HemisphereLight("#dbe9ff", "#243026", 1.7);
    this.scene.add(hemisphere);

    const sun = new THREE.DirectionalLight("#fff1d0", 2.4);
    sun.position.set(-12, 24, 10);
    sun.castShadow = true;
    sun.shadow.mapSize.set(2048, 2048);
    sun.shadow.camera.left = -18;
    sun.shadow.camera.right = 18;
    sun.shadow.camera.top = 24;
    sun.shadow.camera.bottom = -24;
    this.scene.add(sun);

    const fill = new THREE.DirectionalLight("#8aa8ff", 0.65);
    fill.position.set(16, 10, -14);
    this.scene.add(fill);
  }

  worldX(value) {
    return value - Number(this.model.lot.width_m) / 2;
  }

  worldZ(value) {
    return value - Number(this.model.lot.depth_m) / 2;
  }

  lotX(value) {
    return value + Number(this.model.lot.width_m) / 2;
  }

  lotZ(value) {
    return value + Number(this.model.lot.depth_m) / 2;
  }

  registerTargetPart(key, label, kind, object, extra = {}) {
    if (!object) return;
    const entry = this.targetParts.get(key) || {
      key,
      label,
      kind,
      objects: [],
      ...extra,
    };
    entry.objects.push(object);
    this.targetParts.set(key, entry);
  }

  addBox({
    width,
    height,
    depth,
    x,
    y,
    z,
    color,
    opacity = 1,
    roughness = 0.82,
  }) {
    const geometry = new THREE.BoxGeometry(width, height, depth);
    const material = new THREE.MeshStandardMaterial({
      color,
      roughness,
      metalness: 0.02,
      transparent: opacity < 1,
      opacity,
    });
    const mesh = new THREE.Mesh(geometry, material);
    mesh.position.set(x, y, z);
    mesh.receiveShadow = true;
    return mesh;
  }

  buildModel() {
    const lot = this.model.lot;
    const building = this.model.building;
    const defaults = this.model.defaults;
    const floorThickness = Number(defaults.floor_thickness_m) || 0.08;

    const lotSlab = this.addBox({
      width: lot.width_m,
      height: 0.12,
      depth: lot.depth_m,
      x: 0,
      y: -0.08,
      z: 0,
      color: lot.color || "#26382b",
      roughness: 1,
    });
    lotSlab.receiveShadow = true;
    this.sceneRoot.add(lotSlab);

    const lotEdges = new THREE.LineSegments(
      new THREE.EdgesGeometry(
        new THREE.BoxGeometry(lot.width_m, 0.13, lot.depth_m),
      ),
      new THREE.LineBasicMaterial({ color: "#98b69e" }),
    );
    lotEdges.position.y = -0.075;
    this.sceneRoot.add(lotEdges);

    for (const zone of this.model.outdoor_zones || []) {
      const zoneCenterX = zone.x_m + zone.width_m / 2;
      const zoneCenterZ = zone.z_m + zone.depth_m / 2;
      const slab = this.addBox({
        width: zone.width_m,
        height: 0.035,
        depth: zone.depth_m,
        x: this.worldX(zoneCenterX),
        y: 0.005,
        z: this.worldZ(zoneCenterZ),
        color: zone.color || "#315f3b",
        opacity: zone.status?.includes("schematic") ? 0.7 : 0.9,
      });
      slab.userData.zone = zone;
      this.sceneRoot.add(slab);
      this.registerTargetPart(`zone:${zone.id}`, zone.label, "zone", slab, {
        source: zone,
      });

      for (const fixture of zone.fixtures || []) {
        this.addOutdoorFixture(zone, fixture);
      }

      if (zone.label_visible) {
        const label = new THREE.Sprite(
          new THREE.SpriteMaterial({
            map: createLabelTexture(zone.label, zone.color || "#526c78"),
            transparent: true,
            depthTest: false,
          }),
        );
        label.scale.set(
          Math.min(2.7, Math.max(1.45, zone.width_m * 1.05)),
          0.54,
          1,
        );
        label.position.set(
          this.worldX(zoneCenterX),
          Number(zone.label_y_m) || 0.42,
          this.worldZ(zoneCenterZ),
        );
        label.renderOrder = 11;
        this.labelSprites.push(label);
        this.sceneRoot.add(label);
        this.registerTargetPart(`zone:${zone.id}`, zone.label, "zone", label, {
          source: zone,
        });
      }
    }

    for (const room of this.model.rooms || []) {
      const globalX = building.origin_x_m + room.x_m;
      const globalZ = building.origin_z_m + room.z_m;
      const floor = this.addBox({
        width: room.width_m,
        height: floorThickness,
        depth: room.depth_m,
        x: this.worldX(globalX + room.width_m / 2),
        y: floorThickness / 2,
        z: this.worldZ(globalZ + room.depth_m / 2),
        color: room.color || "#777777",
      });
      floor.userData.room = room;
      floor.userData.baseEmissive = new THREE.Color("#000000");
      floor.material.emissive = floor.userData.baseEmissive.clone();
      floor.material.emissiveIntensity = 0;
      this.roomMeshes.push(floor);
      this.sceneRoot.add(floor);
      this.registerTargetPart(`room:${room.id}`, room.label, "room", floor, {
        source: room,
      });

      const label = new THREE.Sprite(
        new THREE.SpriteMaterial({
          map: createLabelTexture(room.label, room.color),
          transparent: true,
          depthTest: false,
        }),
      );
      label.scale.set(
        Math.min(2.5, Math.max(1.35, room.width_m * 0.72)),
        0.54,
        1,
      );
      label.position.set(
        this.worldX(globalX + room.width_m / 2),
        0.34,
        this.worldZ(globalZ + room.depth_m / 2),
      );
      label.renderOrder = 10;
      this.labelSprites.push(label);
      this.sceneRoot.add(label);
      this.registerTargetPart(`room:${room.id}`, room.label, "room", label, {
        source: room,
      });
    }

    for (const wall of this.model.walls || []) this.buildWall(wall);

    this.roof = this.addBox({
      width: building.width_m + 0.3,
      height: 0.1,
      depth: building.depth_m + 0.3,
      x: this.worldX(building.origin_x_m + building.width_m / 2),
      y: building.roof?.height_m || 2.88,
      z: this.worldZ(building.origin_z_m + building.depth_m / 2),
      color: "#a96f50",
      opacity: 0.34,
      roughness: 0.7,
    });
    this.roof.visible = this.roofVisible;
    this.sceneRoot.add(this.roof);
    this.registerTargetPart("roof:main", "Cobertura", "roof", this.roof, {
      source: building.roof || {},
    });

    const buildingCenterX = this.worldX(
      building.origin_x_m + building.width_m / 2,
    );
    const buildingCenterZ = this.worldZ(
      building.origin_z_m + building.depth_m / 2,
    );
    this.target = new THREE.Vector3(buildingCenterX, 0.35, buildingCenterZ);
  }

  physicalBounds(objects) {
    const bounds = new THREE.Box3();
    for (const object of objects) {
      object.traverse((child) => {
        if (child.isMesh && !child.userData?.isTransformGizmo)
          bounds.expandByObject(child);
      });
    }
    return bounds;
  }

  makeTargetGroup(entry) {
    this.sceneRoot.updateMatrixWorld(true);
    const bounds = this.physicalBounds(entry.objects);
    const center = bounds.isEmpty()
      ? new THREE.Vector3()
      : bounds.getCenter(new THREE.Vector3());
    const baseDimensions = bounds.isEmpty()
      ? new THREE.Vector3(1, 1, 1)
      : bounds.getSize(new THREE.Vector3());
    const group = new THREE.Group();
    group.name = `EditorTarget:${entry.key}`;
    group.position.copy(center);
    this.sceneRoot.add(group);
    for (const object of entry.objects) {
      group.attach(object);
      object.traverse((child) => {
        child.userData.editorTarget = group;
      });
    }
    group.userData.editor = {
      key: entry.key,
      label: entry.label,
      kind: entry.kind,
      source: entry.source || {},
      zone: entry.zone || null,
      basePosition: group.position.clone(),
      baseRotationY: group.rotation.y,
      baseScale: group.scale.clone(),
      baseDimensions,
      isPlacedAsset: false,
    };
    const override = this.layoutOverrides[entry.key];
    if (override) this.applyOverride(group, override);
    this.editorTargets.push(group);
    return group;
  }

  applyOverride(group, override) {
    const editor = group.userData.editor;
    const translation = override.translation_m || {};
    const scale = override.scale || {};
    group.position
      .copy(editor.basePosition)
      .add(
        new THREE.Vector3(
          Number(translation.x) || 0,
          Number(translation.y) || 0,
          Number(translation.z) || 0,
        ),
      );
    group.rotation.y =
      editor.baseRotationY +
      THREE.MathUtils.degToRad(Number(override.rotation_y_deg) || 0);
    group.scale.set(
      Number(scale.x) || 1,
      Number(scale.y) || 1,
      Number(scale.z) || 1,
    );
  }

  async hydrateAssetGroup(group, definition, dimensions) {
    try {
      const template = await loadAssetTemplate(definition);
      if (!template || this.disposed || !group.parent) return;
      const model = template.clone(true);
      model.updateMatrixWorld(true);
      const sourceBounds = new THREE.Box3().setFromObject(model);
      const sourceSize = sourceBounds.getSize(new THREE.Vector3());
      if (
        !Number.isFinite(sourceSize.x) ||
        sourceSize.x <= 0 ||
        sourceSize.y <= 0 ||
        sourceSize.z <= 0
      ) {
        throw new Error("o arquivo não contém uma geometria dimensionável");
      }
      model.scale.set(
        dimensions.width / sourceSize.x,
        dimensions.height / sourceSize.y,
        dimensions.depth / sourceSize.z,
      );
      model.updateMatrixWorld(true);
      const fittedBounds = new THREE.Box3().setFromObject(model);
      const fittedCenter = fittedBounds.getCenter(new THREE.Vector3());
      model.position.set(
        -fittedCenter.x,
        -dimensions.height / 2 - fittedBounds.min.y,
        -fittedCenter.z,
      );
      model.name = `${definition.label} model`;
      model.userData.localAssetModel = true;
      model.traverse((child) => {
        child.userData.editorTarget = group;
        child.userData.sharedAssetResource = true;
        if (child.isMesh) {
          child.castShadow = true;
          child.receiveShadow = true;
        }
      });
      const placeholders = group.children.filter(
        (child) => child.userData.assetPlaceholder,
      );
      for (const placeholder of placeholders) {
        group.remove(placeholder);
        placeholder.geometry?.dispose();
        disposeMaterial(placeholder.material);
      }
      group.add(model);
      group.userData.editor.modelState = "ready";
      if (this.selectedTarget === group) {
        this.selectionBox.update();
        this.notifyEditor(`${definition.label} carregado do acervo local.`);
      }
      this.requestRender();
    } catch (error) {
      group.userData.editor.modelState = "fallback";
      group.userData.editor.modelError = String(error?.message || error);
      this.setStatus(
        `${definition.label}: modelo local indisponível; exibindo volume de segurança.`,
        "err",
      );
      if (this.selectedTarget === group)
        this.notifyEditor(
          `${definition.label}: falha ao carregar; usando volume de segurança.`,
        );
    }
  }

  createAssetGroup(asset, ghost = false) {
    const group = new THREE.Group();
    const definition = ASSET_CATALOG[asset.asset_type] || {};
    const width = Number(asset.width_m) || 0.6;
    const height = Number(asset.height_m) || 0.6;
    const depth = Number(asset.depth_m) || 0.6;
    const body = this.addBox({
      width,
      height,
      depth,
      x: 0,
      y: 0,
      z: 0,
      color: asset.color || "#a88d72",
      opacity: ghost ? 0.42 : 1,
      roughness: 0.72,
    });
    body.castShadow = !ghost;
    body.userData.assetPlaceholder = true;
    group.add(body);
    if (!ghost) {
      const edge = new THREE.LineSegments(
        new THREE.EdgesGeometry(body.geometry),
        new THREE.LineBasicMaterial({
          color: "#f1c40f",
          transparent: true,
          opacity: 0.38,
        }),
      );
      edge.userData.assetPlaceholder = true;
      group.add(edge);
    }
    group.position.set(
      this.worldX(Number(asset.x_m) + width / 2),
      Number(asset.y_m || 0) + height / 2,
      this.worldZ(Number(asset.z_m) + depth / 2),
    );
    group.rotation.y = THREE.MathUtils.degToRad(
      Number(asset.rotation_y_deg) || 0,
    );
    group.userData.editor = {
      key: `asset:${asset.id}`,
      label: asset.label || asset.asset_type,
      kind: "asset",
      asset,
      basePosition: group.position.clone(),
      baseRotationY: group.rotation.y,
      baseScale: group.scale.clone(),
      baseDimensions: new THREE.Vector3(width, height, depth),
      isPlacedAsset: true,
      modelState: definition.modelUrl ? "loading" : "primitive",
    };
    group.traverse((child) => {
      child.userData.editorTarget = group;
    });
    if (!ghost && definition.modelUrl)
      this.hydrateAssetGroup(group, definition, { width, height, depth });
    return group;
  }

  buildEditor() {
    for (const entry of this.targetParts.values()) this.makeTargetGroup(entry);
    for (const asset of this.placedAssets) {
      const group = this.createAssetGroup(asset);
      this.sceneRoot.add(group);
      this.editorTargets.push(group);
      this.placedAssetGroups.push(group);
    }

    this.selectionBox = new THREE.BoxHelper(new THREE.Group(), "#f1c40f");
    this.selectionBox.visible = false;
    this.selectionBox.material.depthTest = false;
    this.selectionBox.material.transparent = true;
    this.selectionBox.material.opacity = 0.9;
    this.selectionBox.renderOrder = 998;
    this.scene.add(this.selectionBox);

    this.transform = new TransformControls(
      this.camera,
      this.renderer.domElement,
    );
    this.transform.visible = false;
    this.transform.addEventListener("change", () => {
      this.selectionBox.update();
      this.transform.update();
      this.requestRender();
    });
    this.transform.addEventListener("dragging-changed", (event) => {
      this.controls.enabled = !event.value;
      this.notifyEditor(
        event.value ? "Transformando objeto…" : "Objeto alterado.",
      );
    });
    this.transform.addEventListener("objectChange", () => {
      this.constrainSelected();
      this.selectionBox.update();
      this.notifyEditor("Alterações pendentes.");
    });
    this.scene.add(this.transform);
  }

  setEditorEnabled(enabled) {
    this.editorEnabled = Boolean(enabled);
    this.host.classList.toggle("editing", this.editorEnabled);
    if (!this.editorEnabled) {
      this.cancelPlacement();
      this.selectTarget(null);
    }
    this.notifyEditor(
      this.editorEnabled
        ? "Clique em um elemento ou adicione um objeto."
        : "Editor desativado.",
    );
    this.requestRender();
  }

  setTransformMode(mode) {
    this.transform.setMode(mode);
    this.notifyEditor(
      `Modo ${mode === "translate" ? "mover" : mode === "rotate" ? "girar" : "escalar"}.`,
    );
  }

  setSnap(value) {
    const snap = Math.max(0, Number(value) || 0);
    this.transform.setTranslationSnap(snap);
    this.transform.setScaleSnap(snap);
    this.transform.setRotationSnap(snap ? THREE.MathUtils.degToRad(15) : 0);
    this.notifyEditor(snap ? `Encaixe de ${snap} m ativo.` : "Encaixe livre.");
  }

  selectionDimensions(target = this.selectedTarget) {
    const editor = target?.userData.editor;
    if (!editor?.baseDimensions) return null;
    return {
      width: editor.baseDimensions.x * target.scale.x,
      height: editor.baseDimensions.y * target.scale.y,
      depth: editor.baseDimensions.z * target.scale.z,
    };
  }

  setSelectedDimensions(dimensions) {
    const target = this.selectedTarget;
    const editor = target?.userData.editor;
    if (!editor?.baseDimensions) return false;
    const values = ["width", "height", "depth"].map((key) =>
      Number(dimensions?.[key]),
    );
    if (
      values.some(
        (value) => !Number.isFinite(value) || value < 0.05 || value > 100,
      )
    ) {
      throw new Error("Use dimensões entre 0,05 m e 100 m.");
    }
    if (editor.isPlacedAsset && values.some((value) => value > 10)) {
      throw new Error("Objetos adicionados aceitam dimensões de até 10 m.");
    }
    const ratios = [
      values[0] / editor.baseDimensions.x,
      values[1] / editor.baseDimensions.y,
      values[2] / editor.baseDimensions.z,
    ];
    if (ratios.some((ratio) => ratio < 0.1 || ratio > 10)) {
      throw new Error(
        "A dimensão deve ficar entre 10% e 1.000% do tamanho original.",
      );
    }
    target.scale.set(...ratios);
    this.constrainSelected();
    this.selectionBox.update();
    this.transform.update();
    this.notifyEditor(
      "Dimensões exatas aplicadas. Salve o layout para persistir.",
    );
    this.requestRender();
    return true;
  }

  selectTarget(target) {
    this.selectedTarget = target || null;
    if (target && this.editorEnabled) {
      this.selectionBox.setFromObject(target);
      this.selectionBox.visible = true;
      this.transform.attach(target);
    } else {
      this.selectionBox.visible = false;
      this.transform.detach();
    }
    this.notifyEditor(
      target
        ? `${target.userData.editor.label} selecionado.`
        : "Nenhum objeto selecionado.",
    );
    this.requestRender();
  }

  notifyEditor(message) {
    const editor = this.selectedTarget?.userData.editor;
    this.host.dispatchEvent(
      new CustomEvent("scene-editor-state", {
        detail: {
          message,
          enabled: this.editorEnabled,
          selected: editor
            ? {
                key: editor.key,
                label: editor.label,
                kind: editor.kind,
                isPlacedAsset: editor.isPlacedAsset,
                dimensions: this.selectionDimensions(),
              }
            : null,
          placing: this.placementType,
        },
      }),
    );
  }

  constrainSelected() {
    if (!this.selectedTarget) return;
    const halfWidth = Number(this.model.lot.width_m) / 2;
    const halfDepth = Number(this.model.lot.depth_m) / 2;
    this.selectedTarget.position.x = THREE.MathUtils.clamp(
      this.selectedTarget.position.x,
      -halfWidth,
      halfWidth,
    );
    this.selectedTarget.position.z = THREE.MathUtils.clamp(
      this.selectedTarget.position.z,
      -halfDepth,
      halfDepth,
    );
    this.selectedTarget.position.y = THREE.MathUtils.clamp(
      this.selectedTarget.position.y,
      -2,
      10,
    );
    this.selectedTarget.scale.set(
      THREE.MathUtils.clamp(this.selectedTarget.scale.x, 0.1, 10),
      THREE.MathUtils.clamp(this.selectedTarget.scale.y, 0.1, 10),
      THREE.MathUtils.clamp(this.selectedTarget.scale.z, 0.1, 10),
    );
  }

  editorTargetFromObject(object) {
    let current = object;
    while (current) {
      if (current.userData?.editorTarget) return current.userData.editorTarget;
      if (current.userData?.editor) return current;
      current = current.parent;
    }
    return null;
  }

  pickEditorTarget(event) {
    this.setPointerFromEvent(event);
    const hits = this.raycaster
      .intersectObjects(this.editorTargets, true)
      .filter((hit) => !hit.object.userData.isTransformGizmo);
    this.selectTarget(
      hits.length ? this.editorTargetFromObject(hits[0].object) : null,
    );
  }

  pointOnLot(event) {
    this.setPointerFromEvent(event);
    const plane = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0);
    return this.raycaster.ray.intersectPlane(plane, new THREE.Vector3());
  }

  beginPlacement(assetType) {
    const definition = ASSET_CATALOG[assetType];
    if (!definition) return;
    this.setEditorEnabled(true);
    this.cancelPlacement();
    this.placementType = assetType;
    this.placementGhost = this.createAssetGroup(
      {
        id: "asset_preview",
        asset_type: assetType,
        label: definition.label,
        x_m: Number(this.model.lot.width_m) / 2,
        z_m: Number(this.model.lot.depth_m) / 2,
        y_m: 0,
        width_m: definition.width,
        height_m: definition.height,
        depth_m: definition.depth,
        color: definition.color,
      },
      true,
    );
    this.sceneRoot.add(this.placementGhost);
    this.host.classList.add("placing");
    this.notifyEditor(
      `${definition.label}: clique no terreno para posicionar.`,
    );
    this.requestRender();
  }

  updatePlacement(event) {
    if (!this.placementType || !this.placementGhost) return;
    const point = this.pointOnLot(event);
    if (!point) return;
    const definition = ASSET_CATALOG[this.placementType];
    const halfWidth = Number(this.model.lot.width_m) / 2;
    const halfDepth = Number(this.model.lot.depth_m) / 2;
    this.placementGhost.position.set(
      THREE.MathUtils.clamp(
        point.x,
        -halfWidth + definition.width / 2,
        halfWidth - definition.width / 2,
      ),
      definition.height / 2,
      THREE.MathUtils.clamp(
        point.z,
        -halfDepth + definition.depth / 2,
        halfDepth - definition.depth / 2,
      ),
    );
    this.requestRender();
  }

  commitPlacement(event) {
    if (!this.placementType) return false;
    this.updatePlacement(event);
    const definition = ASSET_CATALOG[this.placementType];
    const id = `asset_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 6)}`;
    const center = this.placementGhost.position;
    const asset = {
      id,
      asset_type: this.placementType,
      label: definition.label,
      x_m: this.lotX(center.x) - definition.width / 2,
      y_m: 0,
      z_m: this.lotZ(center.z) - definition.depth / 2,
      width_m: definition.width,
      height_m: definition.height,
      depth_m: definition.depth,
      rotation_y_deg: 0,
      color: definition.color,
      parent_kind: "lot",
      parent_id: "",
      status: "user_placed",
    };
    const group = this.createAssetGroup(asset);
    this.sceneRoot.add(group);
    this.editorTargets.push(group);
    this.placedAssetGroups.push(group);
    this.placedAssets.push(asset);
    this.cancelPlacement();
    this.selectTarget(group);
    this.notifyEditor(
      `${definition.label} adicionado. Salve o layout para persistir.`,
    );
    return true;
  }

  cancelPlacement() {
    if (this.placementGhost) {
      this.sceneRoot.remove(this.placementGhost);
      this.placementGhost.traverse((object) => {
        object.geometry?.dispose();
        disposeMaterial(object.material);
      });
    }
    this.placementGhost = null;
    this.placementType = "";
    this.host.classList.remove("placing");
  }

  duplicateSelected() {
    const editor = this.selectedTarget?.userData.editor;
    if (!editor?.isPlacedAsset) return false;
    const source = this.serializeAsset(this.selectedTarget);
    source.id = `asset_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 6)}`;
    source.label = `${source.label} cópia`;
    source.x_m = Math.min(
      Number(this.model.lot.width_m) - source.width_m,
      source.x_m + 0.35,
    );
    source.z_m = Math.min(
      Number(this.model.lot.depth_m) - source.depth_m,
      source.z_m + 0.35,
    );
    const group = this.createAssetGroup(source);
    this.sceneRoot.add(group);
    this.editorTargets.push(group);
    this.placedAssetGroups.push(group);
    this.placedAssets.push(source);
    this.selectTarget(group);
    return true;
  }

  deleteSelected() {
    const target = this.selectedTarget;
    const editor = target?.userData.editor;
    if (!editor?.isPlacedAsset) return false;
    this.selectTarget(null);
    this.sceneRoot.remove(target);
    this.editorTargets = this.editorTargets.filter((item) => item !== target);
    this.placedAssetGroups = this.placedAssetGroups.filter(
      (item) => item !== target,
    );
    this.placedAssets = this.placedAssets.filter(
      (item) => item.id !== editor.asset.id,
    );
    target.traverse((object) => {
      if (object.userData.sharedAssetResource) return;
      object.geometry?.dispose();
      disposeMaterial(object.material);
    });
    this.notifyEditor("Objeto excluído. Salve o layout para persistir.");
    return true;
  }

  resetSelected() {
    const target = this.selectedTarget;
    const editor = target?.userData.editor;
    if (!editor) return false;
    target.position.copy(editor.basePosition);
    target.rotation.y = editor.baseRotationY;
    target.scale.copy(editor.baseScale);
    if (!editor.isPlacedAsset) delete this.layoutOverrides[editor.key];
    this.selectionBox.update();
    this.transform.update();
    this.notifyEditor("Transformação restaurada.");
    this.requestRender();
    return true;
  }

  serializeAsset(group) {
    const editor = group.userData.editor;
    const source = editor.asset;
    const width = Number(source.width_m) * group.scale.x;
    const height = Number(source.height_m) * group.scale.y;
    const depth = Number(source.depth_m) * group.scale.z;
    return {
      ...source,
      x_m: THREE.MathUtils.clamp(
        this.lotX(group.position.x) - width / 2,
        0,
        Number(this.model.lot.width_m) - width,
      ),
      y_m: Math.max(0, group.position.y - height / 2),
      z_m: THREE.MathUtils.clamp(
        this.lotZ(group.position.z) - depth / 2,
        0,
        Number(this.model.lot.depth_m) - depth,
      ),
      width_m: width,
      height_m: height,
      depth_m: depth,
      rotation_y_deg: THREE.MathUtils.radToDeg(group.rotation.y),
    };
  }

  getLayoutState() {
    const overrides = {};
    for (const group of this.editorTargets) {
      const editor = group.userData.editor;
      if (!editor || editor.isPlacedAsset) continue;
      const translation = group.position.clone().sub(editor.basePosition);
      const rotation = THREE.MathUtils.radToDeg(
        group.rotation.y - editor.baseRotationY,
      );
      const changed =
        translation.lengthSq() > 0.000001 ||
        Math.abs(rotation) > 0.001 ||
        group.scale.distanceTo(editor.baseScale) > 0.0001;
      if (changed) {
        overrides[editor.key] = {
          translation_m: {
            x: translation.x,
            y: translation.y,
            z: translation.z,
          },
          rotation_y_deg: rotation,
          scale: { x: group.scale.x, y: group.scale.y, z: group.scale.z },
        };
      }
    }
    return {
      layout_overrides: overrides,
      placed_assets: this.placedAssetGroups.map((group) =>
        this.serializeAsset(group),
      ),
    };
  }

  buildWall(wall) {
    const building = this.model.building;
    const defaults = this.model.defaults;
    const start = new THREE.Vector2(
      this.worldX(building.origin_x_m + wall.start[0]),
      this.worldZ(building.origin_z_m + wall.start[1]),
    );
    const end = new THREE.Vector2(
      this.worldX(building.origin_x_m + wall.end[0]),
      this.worldZ(building.origin_z_m + wall.end[1]),
    );
    const vector = end.clone().sub(start);
    const length = vector.length();
    if (!length) return;
    const direction = vector.clone().normalize();
    const wallHeight = Number(wall.height_m || defaults.wall_height_m) || 2.7;
    const thickness =
      Number(wall.thickness_m || defaults.wall_thickness_m) || 0.14;
    const wallColor = wall.kind === "exterior" ? "#dedbd2" : "#c8c5bc";
    const openings = [...(wall.openings || [])]
      .map((opening) => ({
        ...opening,
        offset_m: Math.max(0, Number(opening.offset_m) || 0),
        width_m: Math.max(0.2, Number(opening.width_m) || 0.8),
      }))
      .sort((a, b) => a.offset_m - b.offset_m);

    let cursor = 0;
    for (const opening of openings) {
      const openingStart = Math.min(length, opening.offset_m);
      const openingEnd = Math.min(length, openingStart + opening.width_m);
      this.addWallPiece(
        start,
        direction,
        cursor,
        openingStart,
        0,
        wallHeight,
        thickness,
        wallColor,
        wall,
      );
      if (opening.type === "window") {
        const sill = Number(opening.sill_m || defaults.window_sill_m) || 1;
        const openingHeight =
          Number(opening.height_m || defaults.window_height_m) || 1.1;
        this.addWallPiece(
          start,
          direction,
          openingStart,
          openingEnd,
          0,
          sill,
          thickness,
          wallColor,
          wall,
        );
        this.addWallPiece(
          start,
          direction,
          openingStart,
          openingEnd,
          Math.min(wallHeight, sill + openingHeight),
          Math.max(0, wallHeight - sill - openingHeight),
          thickness,
          wallColor,
          wall,
        );
        this.addOpeningGlass(
          start,
          direction,
          openingStart,
          openingEnd,
          sill,
          openingHeight,
          thickness,
          "#72b8d4",
          wall,
        );
      } else {
        const doorHeight =
          Number(opening.height_m || defaults.door_height_m) || 2.1;
        this.addWallPiece(
          start,
          direction,
          openingStart,
          openingEnd,
          doorHeight,
          Math.max(0, wallHeight - doorHeight),
          thickness,
          wallColor,
          wall,
        );
        if (opening.frame) {
          this.addOpeningFrame(
            start,
            direction,
            openingStart,
            openingEnd,
            doorHeight,
            thickness,
            wall,
          );
        }
      }
      cursor = openingEnd;
    }
    this.addWallPiece(
      start,
      direction,
      cursor,
      length,
      0,
      wallHeight,
      thickness,
      wallColor,
      wall,
    );
  }

  addWallPiece(
    start,
    direction,
    from,
    to,
    bottom,
    height,
    thickness,
    color,
    wall,
  ) {
    const width = to - from;
    if (width <= 0.01 || height <= 0.01) return;
    const centerDistance = (from + to) / 2;
    const center = start
      .clone()
      .add(direction.clone().multiplyScalar(centerDistance));
    const mesh = this.addBox({
      width,
      height,
      depth: thickness,
      x: center.x,
      y: bottom + height / 2,
      z: center.y,
      color,
      roughness: 0.92,
    });
    mesh.rotation.y = -Math.atan2(direction.y, direction.x);
    mesh.castShadow = true;
    mesh.userData.wall = wall;
    this.wallMeshes.push(mesh);
    this.sceneRoot.add(mesh);
    this.registerTargetPart(
      `wall:${wall.id}`,
      wall.label || wall.id,
      "wall",
      mesh,
      { source: wall },
    );
  }

  addOutdoorFixture(zone, fixture) {
    const width = Math.max(0.08, Number(fixture.width_m) || 0.5);
    const depth = Math.max(0.08, Number(fixture.depth_m) || 0.5);
    const height = Math.max(0.02, Number(fixture.height_m) || 0.5);
    const globalX = zone.x_m + (Number(fixture.x_m) || 0);
    const globalZ = zone.z_m + (Number(fixture.z_m) || 0);
    const mesh = this.addBox({
      width,
      height,
      depth,
      x: this.worldX(globalX + width / 2),
      y: height / 2 + 0.035,
      z: this.worldZ(globalZ + depth / 2),
      color: fixture.color || "#9aa4a8",
      roughness: fixture.type === "appliance" ? 0.42 : 0.8,
    });
    mesh.castShadow = true;
    mesh.userData.zone = zone;
    mesh.userData.fixture = fixture;
    this.sceneRoot.add(mesh);
    const fixtureKey = `fixture:${zone.id}:${fixture.id}`;
    this.registerTargetPart(
      fixtureKey,
      fixture.label || fixture.id,
      "fixture",
      mesh,
      { source: fixture, zone },
    );

    if (fixture.accent_color) {
      const accent = this.addBox({
        width: width * 0.58,
        height: height * 0.44,
        depth: 0.025,
        x: this.worldX(globalX + width / 2),
        y: 0.035 + height * 0.56,
        z: this.worldZ(globalZ + 0.012),
        color: fixture.accent_color,
        roughness: 0.28,
      });
      this.sceneRoot.add(accent);
      this.registerTargetPart(
        fixtureKey,
        fixture.label || fixture.id,
        "fixture",
        accent,
        { source: fixture, zone },
      );
    }
  }

  addOpeningFrame(start, direction, from, to, height, thickness, wall) {
    const frameWidth = Math.min(0.07, Math.max(0.045, (to - from) * 0.04));
    const frameDepth = thickness * 1.35;
    const frameColor = "#506776";
    this.addWallPiece(
      start,
      direction,
      from,
      from + frameWidth,
      0,
      height,
      frameDepth,
      frameColor,
      wall,
    );
    this.addWallPiece(
      start,
      direction,
      to - frameWidth,
      to,
      0,
      height,
      frameDepth,
      frameColor,
      wall,
    );
    this.addWallPiece(
      start,
      direction,
      from,
      to,
      height - frameWidth,
      frameWidth,
      frameDepth,
      frameColor,
      wall,
    );
    this.addWallPiece(
      start,
      direction,
      from,
      to,
      0,
      0.045,
      frameDepth,
      frameColor,
      wall,
    );
  }

  addOpeningGlass(
    start,
    direction,
    from,
    to,
    bottom,
    height,
    thickness,
    color,
    wall,
  ) {
    const width = to - from;
    const center = start
      .clone()
      .add(direction.clone().multiplyScalar((from + to) / 2));
    const glass = this.addBox({
      width: width * 0.94,
      height: height * 0.94,
      depth: thickness * 0.3,
      x: center.x,
      y: bottom + height / 2,
      z: center.y,
      color,
      opacity: 0.35,
      roughness: 0.15,
    });
    glass.rotation.y = -Math.atan2(direction.y, direction.x);
    glass.userData.wall = wall;
    this.sceneRoot.add(glass);
    this.registerTargetPart(
      `wall:${wall.id}`,
      wall.label || wall.id,
      "wall",
      glass,
      { source: wall },
    );
  }

  buildLegend() {
    if (!this.legend) return;
    this.legend.replaceChildren();
    const kinds = new Map();
    for (const room of this.model.rooms || []) {
      if (!kinds.has(room.kind)) kinds.set(room.kind, room);
    }
    for (const room of kinds.values()) {
      const item = document.createElement("span");
      const swatch = document.createElement("i");
      swatch.style.backgroundColor = room.color;
      item.append(swatch, document.createTextNode(this.kindLabel(room.kind)));
      this.legend.appendChild(item);
    }
  }

  kindLabel(kind) {
    return (
      {
        bedroom: "Quarto",
        bathroom: "Banheiro",
        circulation: "Circulação",
        office: "Escritório",
        living: "Sala",
      }[kind] || kind
    );
  }

  bindInteractions() {
    this.onToolbarClick = (event) => {
      const button = event.currentTarget;
      if (!button) return;
      const action = button.getAttribute("data-3d-action");
      if (action === "perspective") this.setPerspective();
      if (action === "top") this.setTopView();
      if (action === "reset") this.setPerspective();
      if (action === "zoom-in") this.zoomCamera(0.82);
      if (action === "zoom-out") this.zoomCamera(1.22);
      if (action === "roof") {
        this.roofVisible = !this.roofVisible;
        this.roof.visible = this.roofVisible;
        button.setAttribute("aria-pressed", String(this.roofVisible));
        this.requestRender();
      }
      if (action === "walls") {
        this.wallsTransparent = !this.wallsTransparent;
        for (const mesh of this.wallMeshes) {
          mesh.material.transparent = this.wallsTransparent;
          mesh.material.opacity = this.wallsTransparent ? 0.34 : 1;
          mesh.material.depthWrite = !this.wallsTransparent;
        }
        button.setAttribute("aria-pressed", String(this.wallsTransparent));
        this.requestRender();
      }
      if (action === "labels") {
        this.labelsVisible = !this.labelsVisible;
        for (const label of this.labelSprites)
          label.visible = this.labelsVisible;
        button.setAttribute("aria-pressed", String(this.labelsVisible));
        this.requestRender();
      }
    };
    this.toolbarButtons = [
      ...(this.toolbar?.querySelectorAll("[data-3d-action]") || []),
    ];
    for (const button of this.toolbarButtons) {
      button.addEventListener("click", this.onToolbarClick);
    }

    this.onPointerDown = (event) => {
      if (this.transform.dragging) return;
      this.pointerStart = { x: event.clientX, y: event.clientY };
    };
    this.onPointerMove = (event) => {
      if (this.placementType) this.updatePlacement(event);
    };
    this.onPointerUp = (event) => {
      if (this.transform.dragging) return;
      if (!this.pointerStart) return;
      const distance = Math.hypot(
        event.clientX - this.pointerStart.x,
        event.clientY - this.pointerStart.y,
      );
      this.pointerStart = null;
      if (distance > 5) return;
      if (this.commitPlacement(event)) return;
      if (this.editorEnabled) this.pickEditorTarget(event);
      else this.pickRoom(event);
    };
    this.onDragOver = (event) => {
      if (!event.dataTransfer?.types.includes("application/x-my-home-asset"))
        return;
      event.preventDefault();
      this.updatePlacement(event);
    };
    this.onDrop = (event) => {
      const assetType = event.dataTransfer?.getData(
        "application/x-my-home-asset",
      );
      if (!assetType) return;
      event.preventDefault();
      if (this.placementType !== assetType) this.beginPlacement(assetType);
      this.commitPlacement(event);
    };
    this.renderer.domElement.addEventListener(
      "pointerdown",
      this.onPointerDown,
    );
    this.renderer.domElement.addEventListener(
      "pointermove",
      this.onPointerMove,
    );
    this.renderer.domElement.addEventListener("pointerup", this.onPointerUp);
    this.renderer.domElement.addEventListener("dragover", this.onDragOver);
    this.renderer.domElement.addEventListener("drop", this.onDrop);
  }

  setPointerFromEvent(event) {
    const rect = this.renderer.domElement.getBoundingClientRect();
    this.pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    this.pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
    this.raycaster.setFromCamera(this.pointer, this.camera);
  }

  pickRoom(event) {
    this.setPointerFromEvent(event);
    const hit = this.raycaster.intersectObjects(this.roomMeshes, false)[0];
    if (!hit) return;
    this.selectRoom(hit.object);
  }

  selectRoom(floor) {
    if (this.selectedFloor) {
      this.selectedFloor.material.emissive.set("#000000");
      this.selectedFloor.material.emissiveIntensity = 0;
    }
    this.selectedFloor = floor;
    floor.material.emissive.set("#f1c40f");
    floor.material.emissiveIntensity = 0.36;
    const room = floor.userData.room;
    if (this.detail) {
      this.detail.replaceChildren();
      const title = document.createElement("strong");
      title.textContent = room.label;
      const dimensions = document.createElement("span");
      dimensions.textContent = `${room.width_m.toFixed(2)} × ${room.depth_m.toFixed(2)} m · ${room.area_m2.toFixed(2)} m²`;
      const source = document.createElement("small");
      source.textContent = `Geometria: ${room.geometry_source}`;
      this.detail.append(title, dimensions, source);
    }
    this.requestRender();
  }

  setPerspective() {
    const target = this.target || new THREE.Vector3();
    this.camera.position.set(target.x + 10.5, 10, target.z + 12.5);
    this.camera.up.set(0, 1, 0);
    this.controls.target.copy(target);
    this.toolbar
      ?.querySelector('[data-3d-action="perspective"]')
      ?.setAttribute("aria-pressed", "true");
    this.toolbar
      ?.querySelector('[data-3d-action="top"]')
      ?.setAttribute("aria-pressed", "false");
    this.controls.update();
    this.requestRender();
  }

  setTopView() {
    const target = this.target || new THREE.Vector3();
    this.camera.position.set(target.x, 16.5, target.z + 0.01);
    this.camera.up.set(0, 0, -1);
    this.controls.target.copy(target);
    this.toolbar
      ?.querySelector('[data-3d-action="perspective"]')
      ?.setAttribute("aria-pressed", "false");
    this.toolbar
      ?.querySelector('[data-3d-action="top"]')
      ?.setAttribute("aria-pressed", "true");
    this.controls.update();
    this.requestRender();
  }

  zoomCamera(factor) {
    const target = this.controls.target;
    const offset = this.camera.position.clone().sub(target);
    const distance = THREE.MathUtils.clamp(
      offset.length() * factor,
      this.controls.minDistance,
      this.controls.maxDistance,
    );
    offset.setLength(distance);
    this.camera.position.copy(target).add(offset);
    this.controls.update();
    this.requestRender();
  }

  cleanRenderState() {
    return {
      transformVisible: this.transform?.visible,
      selectionVisible: this.selectionBox?.visible,
      ghostVisible: this.placementGhost?.visible,
    };
  }

  setCleanRender(enabled, saved = null) {
    if (enabled) {
      if (this.transform) this.transform.visible = false;
      if (this.selectionBox) this.selectionBox.visible = false;
      if (this.placementGhost) this.placementGhost.visible = false;
      return;
    }
    if (this.transform)
      this.transform.visible = Boolean(saved?.transformVisible);
    if (this.selectionBox)
      this.selectionBox.visible = Boolean(saved?.selectionVisible);
    if (this.placementGhost)
      this.placementGhost.visible = Boolean(saved?.ghostVisible);
  }

  captureSnapshot(mimeType = "image/png") {
    if (this.recording)
      return Promise.reject(
        new Error("Finalize a gravação antes de tirar a foto."),
      );
    const type = mimeType === "image/jpeg" ? "image/jpeg" : "image/png";
    const originalPixelRatio = this.renderer.getPixelRatio();
    const originalAspect = this.camera.aspect;
    const cleanState = this.cleanRenderState();
    const width = 1920;
    const height = 1080;
    this.setCleanRender(true);
    this.renderer.setPixelRatio(1);
    this.renderer.setSize(width, height, false);
    this.camera.aspect = width / height;
    this.camera.updateProjectionMatrix();
    this.renderer.render(this.scene, this.camera);
    return new Promise((resolve, reject) => {
      this.renderer.domElement.toBlob(
        (blob) => {
          this.renderer.setPixelRatio(originalPixelRatio);
          this.camera.aspect = originalAspect;
          this.camera.updateProjectionMatrix();
          this.resize();
          this.setCleanRender(false, cleanState);
          this.requestRender();
          if (blob) resolve(blob);
          else reject(new Error("O navegador não conseguiu criar a imagem."));
        },
        type,
        type === "image/jpeg" ? 0.92 : undefined,
      );
    });
  }

  recordingMimeType() {
    if (!window.MediaRecorder) return "";
    return (
      ["video/webm;codecs=vp9", "video/webm;codecs=vp8", "video/webm"].find(
        (type) => MediaRecorder.isTypeSupported(type),
      ) || ""
    );
  }

  notifyMediaProgress(elapsed, duration, state = "recording") {
    this.host.dispatchEvent(
      new CustomEvent("scene-media-progress", {
        detail: {
          state,
          elapsedMs: elapsed,
          durationMs: duration,
          progress: duration ? Math.min(1, elapsed / duration) : 0,
        },
      }),
    );
  }

  startRecording({ mode = "orbit", durationSeconds = 10 } = {}) {
    if (this.recording)
      return Promise.reject(new Error("Já existe uma gravação em andamento."));
    if (!this.renderer.domElement.captureStream || !window.MediaRecorder) {
      return Promise.reject(
        new Error("Este navegador não oferece gravação do canvas."),
      );
    }
    const durationMs =
      THREE.MathUtils.clamp(Number(durationSeconds) || 10, 3, 30) * 1000;
    const mimeType = this.recordingMimeType();
    const stream = this.renderer.domElement.captureStream(30);
    const recorder = new MediaRecorder(stream, {
      ...(mimeType ? { mimeType } : {}),
      videoBitsPerSecond: 4_000_000,
    });
    const chunks = [];
    const cameraState = {
      position: this.camera.position.clone(),
      quaternion: this.camera.quaternion.clone(),
      up: this.camera.up.clone(),
      target: this.controls.target.clone(),
      controlsEnabled: this.controls.enabled,
      clean: this.cleanRenderState(),
    };
    this.setCleanRender(true);
    if (mode === "orbit") this.controls.enabled = false;
    const offset = this.camera.position.clone().sub(this.controls.target);
    const radius = Math.max(2, Math.hypot(offset.x, offset.z));
    const initialAngle = Math.atan2(offset.z, offset.x);
    const startedAt = performance.now();

    return new Promise((resolve, reject) => {
      const finish = () => {
        cancelAnimationFrame(this.recording?.animationFrame || 0);
        stream.getTracks().forEach((track) => track.stop());
        this.camera.position.copy(cameraState.position);
        this.camera.quaternion.copy(cameraState.quaternion);
        this.camera.up.copy(cameraState.up);
        this.controls.target.copy(cameraState.target);
        this.controls.enabled = cameraState.controlsEnabled;
        this.setCleanRender(false, cameraState.clean);
        this.controls.update();
        this.recording = null;
        this.requestRender();
      };
      recorder.ondataavailable = (event) => {
        if (event.data?.size) chunks.push(event.data);
      };
      recorder.onerror = (event) => {
        finish();
        reject(event.error || new Error("Falha durante a gravação."));
      };
      recorder.onstop = () => {
        finish();
        const blob = new Blob(chunks, {
          type: recorder.mimeType || mimeType || "video/webm",
        });
        this.notifyMediaProgress(durationMs, durationMs, "complete");
        blob.size
          ? resolve(blob)
          : reject(new Error("A gravação não gerou dados."));
      };
      const renderFrame = (now) => {
        if (!this.recording) return;
        const elapsed = Math.min(durationMs, now - startedAt);
        if (mode === "orbit") {
          const angle = initialAngle + (elapsed / durationMs) * Math.PI * 2;
          this.camera.position.set(
            this.controls.target.x + Math.cos(angle) * radius,
            cameraState.position.y,
            this.controls.target.z + Math.sin(angle) * radius,
          );
          this.camera.lookAt(this.controls.target);
        }
        this.renderer.render(this.scene, this.camera);
        this.notifyMediaProgress(elapsed, durationMs);
        if (elapsed >= durationMs) {
          if (recorder.state !== "inactive") recorder.stop();
          return;
        }
        this.recording.animationFrame = requestAnimationFrame(renderFrame);
      };
      this.recording = { recorder, stream, animationFrame: 0 };
      recorder.start(500);
      this.notifyMediaProgress(0, durationMs);
      this.recording.animationFrame = requestAnimationFrame(renderFrame);
    });
  }

  stopRecording() {
    if (!this.recording || this.recording.recorder.state === "inactive")
      return false;
    this.recording.recorder.stop();
    return true;
  }

  resize() {
    const width = Math.max(1, this.host.clientWidth);
    const height = Math.max(1, this.host.clientHeight);
    this.camera.aspect = width / height;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(width, height, false);
    this.requestRender();
  }

  requestRender() {
    if (this.renderPending) return;
    this.renderPending = true;
    requestAnimationFrame(() => {
      this.renderPending = false;
      this.renderer.render(this.scene, this.camera);
    });
  }

  dispose() {
    this.disposed = true;
    this.stopRecording();
    this.resizeObserver?.disconnect();
    for (const button of this.toolbarButtons || []) {
      button.removeEventListener("click", this.onToolbarClick);
    }
    this.renderer?.domElement.removeEventListener(
      "pointerdown",
      this.onPointerDown,
    );
    this.renderer?.domElement.removeEventListener(
      "pointerup",
      this.onPointerUp,
    );
    this.renderer?.domElement.removeEventListener(
      "pointermove",
      this.onPointerMove,
    );
    this.renderer?.domElement.removeEventListener("dragover", this.onDragOver);
    this.renderer?.domElement.removeEventListener("drop", this.onDrop);
    this.transform?.dispose();
    this.controls?.dispose();
    this.scene?.traverse((object) => {
      if (object.userData.sharedAssetResource) return;
      object.geometry?.dispose();
      disposeMaterial(object.material);
    });
    this.renderer?.dispose();
    this.renderer?.domElement.remove();
  }
}

export function mountHouse3D(model) {
  const fingerprint = JSON.stringify(model || {});
  if (!model || !Array.isArray(model.rooms) || !model.rooms.length) {
    const status = byId("house-3d-status");
    if (status) {
      status.textContent = "Geometria 3D ainda não disponível.";
      status.classList.add("err");
    }
    return null;
  }
  if (activeViewer && activeFingerprint === fingerprint) {
    activeViewer.resize();
    activeViewer.setStatus(
      "Modelo pronto — arraste para girar, role para aproximar.",
      "ok",
    );
    return activeViewer;
  }
  activeViewer?.dispose();
  activeFingerprint = fingerprint;
  try {
    activeViewer = new HouseViewer(model);
    return activeViewer;
  } catch (error) {
    activeViewer = null;
    const status = byId("house-3d-status");
    if (status) {
      status.textContent = `Não foi possível abrir o modelo 3D: ${error.message || error}`;
      status.classList.add("err");
    }
    throw error;
  }
}

export function resizeHouse3D() {
  activeViewer?.resize();
}

export function setSceneEditorEnabled(enabled) {
  activeViewer?.setEditorEnabled(enabled);
}

export function setSceneTransformMode(mode) {
  activeViewer?.setTransformMode(mode);
}

export function setSceneSnap(value) {
  activeViewer?.setSnap(value);
}

export function beginSceneAssetPlacement(assetType) {
  activeViewer?.beginPlacement(assetType);
}

export function getSceneAssetCatalog() {
  return Object.entries(ASSET_CATALOG).map(([id, definition]) => ({
    id,
    ...definition,
  }));
}

export function duplicateSceneSelection() {
  return activeViewer?.duplicateSelected() || false;
}

export function deleteSceneSelection() {
  return activeViewer?.deleteSelected() || false;
}

export function resetSceneSelection() {
  return activeViewer?.resetSelected() || false;
}

export function setSceneSelectionDimensions(dimensions) {
  if (!activeViewer) return false;
  return activeViewer.setSelectedDimensions(dimensions);
}

export function getSceneLayoutState() {
  return (
    activeViewer?.getLayoutState() || {
      layout_overrides: {},
      placed_assets: [],
    }
  );
}

export function captureHouseSnapshot(mimeType) {
  if (!activeViewer)
    return Promise.reject(new Error("Modelo 3D ainda não está pronto."));
  return activeViewer.captureSnapshot(mimeType);
}

export function startHouseRecording(options) {
  if (!activeViewer)
    return Promise.reject(new Error("Modelo 3D ainda não está pronto."));
  return activeViewer.startRecording(options);
}

export function stopHouseRecording() {
  return activeViewer?.stopRecording() || false;
}
