import * as THREE from "three";
import { OrbitControls } from "/vendor/three/OrbitControls.js";

let activeViewer = null;
let activeFingerprint = "";

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
    this.renderPending = false;
    this.pointerStart = null;
    this.selectedFloor = null;
    this.roofVisible = false;
    this.labelsVisible = true;
    this.wallsTransparent = false;

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
    this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
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

    const buildingCenterX = this.worldX(
      building.origin_x_m + building.width_m / 2,
    );
    const buildingCenterZ = this.worldZ(
      building.origin_z_m + building.depth_m / 2,
    );
    this.target = new THREE.Vector3(buildingCenterX, 0.35, buildingCenterZ);
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
    }
  }

  addOpeningFrame(start, direction, from, to, height, thickness, wall) {
    const frameWidth = Math.min(0.07, Math.max(0.045, (to - from) * 0.04));
    const frameDepth = thickness * 1.35;
    const frameColor = "#506776";
    this.addWallPiece(start, direction, from, from + frameWidth, 0, height, frameDepth, frameColor, wall);
    this.addWallPiece(start, direction, to - frameWidth, to, 0, height, frameDepth, frameColor, wall);
    this.addWallPiece(start, direction, from, to, height - frameWidth, frameWidth, frameDepth, frameColor, wall);
    this.addWallPiece(start, direction, from, to, 0, 0.045, frameDepth, frameColor, wall);
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
    this.sceneRoot.add(glass);
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
      this.pointerStart = { x: event.clientX, y: event.clientY };
    };
    this.onPointerUp = (event) => {
      if (!this.pointerStart) return;
      const distance = Math.hypot(
        event.clientX - this.pointerStart.x,
        event.clientY - this.pointerStart.y,
      );
      this.pointerStart = null;
      if (distance > 5) return;
      this.pickRoom(event);
    };
    this.renderer.domElement.addEventListener(
      "pointerdown",
      this.onPointerDown,
    );
    this.renderer.domElement.addEventListener("pointerup", this.onPointerUp);
  }

  pickRoom(event) {
    const rect = this.renderer.domElement.getBoundingClientRect();
    this.pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    this.pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
    this.raycaster.setFromCamera(this.pointer, this.camera);
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

  resize() {
    const width = Math.max(1, this.host.clientWidth);
    const height = Math.max(320, this.host.clientHeight);
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
    this.controls?.dispose();
    this.scene?.traverse((object) => {
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
