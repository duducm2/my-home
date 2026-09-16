import * as THREE from "three";

const COLORS = { X: 0xe74c3c, Y: 0x2ecc71, Z: 0x3498db, XYZ: 0xf1c40f };

function material(color) {
  return new THREE.MeshBasicMaterial({
    color,
    depthTest: false,
    depthWrite: false,
    transparent: true,
    opacity: 0.92,
    toneMapped: false,
  });
}

function lineMaterial(color) {
  return new THREE.LineBasicMaterial({
    color,
    depthTest: false,
    depthWrite: false,
    transparent: true,
    opacity: 0.92,
    toneMapped: false,
  });
}

/**
 * Compact local transform gizmo compatible with this app's Three.js viewer.
 * It intentionally supports the editor's required translate/rotate/scale
 * operations without pulling a build system into the standalone repository.
 */
class TransformControls extends THREE.Group {
  constructor(camera, domElement) {
    super();
    this.camera = camera;
    this.domElement = domElement;
    this.object = null;
    this.mode = "translate";
    this.dragging = false;
    this.translationSnap = 0;
    this.rotationSnap = 0;
    this.scaleSnap = 0;
    this.size = 1;
    this.raycaster = new THREE.Raycaster();
    this.pointer = new THREE.Vector2();
    this.dragPlane = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0);
    this.startPoint = new THREE.Vector3();
    this.startPosition = new THREE.Vector3();
    this.startRotation = new THREE.Euler();
    this.startScale = new THREE.Vector3();
    this.startClient = { x: 0, y: 0 };
    this.axis = "XYZ";
    this.visible = false;
    this.renderOrder = 1000;
    this.userData.isTransformGizmo = true;

    this.translateGroup = this._buildTranslate();
    this.rotateGroup = this._buildRotate();
    this.scaleGroup = this._buildScale();
    this.add(this.translateGroup, this.rotateGroup, this.scaleGroup);
    this.setMode("translate");

    this._onPointerDown = (event) => this._pointerDown(event);
    this._onPointerMove = (event) => this._pointerMove(event);
    this._onPointerUp = (event) => this._pointerUp(event);
    domElement.addEventListener("pointerdown", this._onPointerDown);
    domElement.addEventListener("pointermove", this._onPointerMove);
    domElement.addEventListener("pointerup", this._onPointerUp);
    domElement.addEventListener("pointercancel", this._onPointerUp);
  }

  _axisLine(axis, vector) {
    const geometry = new THREE.BufferGeometry().setFromPoints([
      new THREE.Vector3(),
      vector.clone().multiplyScalar(1.15),
    ]);
    const line = new THREE.Line(geometry, lineMaterial(COLORS[axis]));
    line.userData.transformAxis = axis;
    line.renderOrder = 1001;
    return line;
  }

  _handle(axis, position, shape = "box") {
    const geometry = shape === "cone"
      ? new THREE.ConeGeometry(0.09, 0.24, 10)
      : new THREE.BoxGeometry(0.16, 0.16, 0.16);
    const handle = new THREE.Mesh(geometry, material(COLORS[axis]));
    handle.position.copy(position);
    if (shape === "cone") {
      if (axis === "X") handle.rotation.z = -Math.PI / 2;
      if (axis === "Z") handle.rotation.x = Math.PI / 2;
    }
    handle.userData.transformAxis = axis;
    handle.renderOrder = 1002;
    return handle;
  }

  _buildTranslate() {
    const group = new THREE.Group();
    group.name = "TranslateGizmo";
    group.add(
      this._axisLine("X", new THREE.Vector3(1, 0, 0)),
      this._axisLine("Y", new THREE.Vector3(0, 1, 0)),
      this._axisLine("Z", new THREE.Vector3(0, 0, 1)),
      this._handle("X", new THREE.Vector3(1.2, 0, 0), "cone"),
      this._handle("Y", new THREE.Vector3(0, 1.2, 0), "cone"),
      this._handle("Z", new THREE.Vector3(0, 0, 1.2), "cone"),
      this._handle("XYZ", new THREE.Vector3(), "box"),
    );
    return group;
  }

  _buildRotate() {
    const group = new THREE.Group();
    group.name = "RotateGizmo";
    const ring = new THREE.Mesh(
      new THREE.TorusGeometry(1, 0.035, 8, 64),
      material(COLORS.Y),
    );
    ring.rotation.x = Math.PI / 2;
    ring.userData.transformAxis = "Y";
    ring.renderOrder = 1002;
    group.add(ring);
    return group;
  }

  _buildScale() {
    const group = new THREE.Group();
    group.name = "ScaleGizmo";
    group.add(
      this._axisLine("X", new THREE.Vector3(1, 0, 0)),
      this._axisLine("Y", new THREE.Vector3(0, 1, 0)),
      this._axisLine("Z", new THREE.Vector3(0, 0, 1)),
      this._handle("X", new THREE.Vector3(1.15, 0, 0)),
      this._handle("Y", new THREE.Vector3(0, 1.15, 0)),
      this._handle("Z", new THREE.Vector3(0, 0, 1.15)),
      this._handle("XYZ", new THREE.Vector3()),
    );
    return group;
  }

  attach(object) {
    this.object = object;
    this.visible = Boolean(object);
    this.update();
    this.dispatchEvent({ type: "change" });
    return this;
  }

  detach() {
    this.object = null;
    this.visible = false;
    this.dragging = false;
    this.dispatchEvent({ type: "change" });
    return this;
  }

  setMode(mode) {
    if (!["translate", "rotate", "scale"].includes(mode)) return this;
    this.mode = mode;
    this.translateGroup.visible = mode === "translate";
    this.rotateGroup.visible = mode === "rotate";
    this.scaleGroup.visible = mode === "scale";
    this.dispatchEvent({ type: "change" });
    return this;
  }

  setTranslationSnap(value) {
    this.translationSnap = Math.max(0, Number(value) || 0);
  }

  setRotationSnap(value) {
    this.rotationSnap = Math.max(0, Number(value) || 0);
  }

  setScaleSnap(value) {
    this.scaleSnap = Math.max(0, Number(value) || 0);
  }

  update() {
    if (!this.object) return;
    this.object.getWorldPosition(this.position);
    const distance = this.camera.position.distanceTo(this.position);
    const scalar = Math.max(0.55, Math.min(2.4, distance * 0.075)) * this.size;
    this.scale.setScalar(scalar);
  }

  _setPointer(event) {
    const rect = this.domElement.getBoundingClientRect();
    this.pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    this.pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
    this.raycaster.setFromCamera(this.pointer, this.camera);
  }

  _pointerDown(event) {
    if (!this.visible || !this.object || event.button !== 0) return;
    this._setPointer(event);
    const hits = this.raycaster.intersectObject(this, true)
      .filter((hit) => hit.object.userData.transformAxis);
    if (!hits.length) return;
    event.preventDefault();
    event.stopPropagation();
    this.axis = hits[0].object.userData.transformAxis;
    this.dragging = true;
    this.startClient = { x: event.clientX, y: event.clientY };
    this.startPosition.copy(this.object.position);
    this.startRotation.copy(this.object.rotation);
    this.startScale.copy(this.object.scale);
    this.dragPlane.constant = -this.object.getWorldPosition(new THREE.Vector3()).y;
    this.raycaster.ray.intersectPlane(this.dragPlane, this.startPoint);
    this.domElement.setPointerCapture?.(event.pointerId);
    this.dispatchEvent({ type: "dragging-changed", value: true });
  }

  _snap(value, step) {
    return step > 0 ? Math.round(value / step) * step : value;
  }

  _pointerMove(event) {
    if (!this.dragging || !this.object) {
      if (this.visible) this.update();
      return;
    }
    event.preventDefault();
    event.stopPropagation();
    const dx = event.clientX - this.startClient.x;
    const dy = event.clientY - this.startClient.y;
    if (this.mode === "translate") {
      this._setPointer(event);
      const point = new THREE.Vector3();
      this.raycaster.ray.intersectPlane(this.dragPlane, point);
      const delta = point.sub(this.startPoint);
      if (this.axis === "X") delta.set(delta.x, 0, 0);
      else if (this.axis === "Z") delta.set(0, 0, delta.z);
      else if (this.axis === "Y") delta.set(0, -dy * 0.015, 0);
      else delta.y = 0;
      this.object.position.set(
        this._snap(this.startPosition.x + delta.x, this.translationSnap),
        this._snap(this.startPosition.y + delta.y, this.translationSnap),
        this._snap(this.startPosition.z + delta.z, this.translationSnap),
      );
    } else if (this.mode === "rotate") {
      const angle = this.startRotation.y + dx * 0.012;
      this.object.rotation.y = this._snap(angle, this.rotationSnap);
    } else {
      const amount = Math.max(0.1, 1 + (dx - dy) * 0.008);
      const next = this.startScale.clone();
      if (this.axis === "XYZ") next.multiplyScalar(amount);
      if (this.axis === "X") next.x *= amount;
      if (this.axis === "Y") next.y *= amount;
      if (this.axis === "Z") next.z *= amount;
      next.set(
        Math.max(0.1, this._snap(next.x, this.scaleSnap)),
        Math.max(0.1, this._snap(next.y, this.scaleSnap)),
        Math.max(0.1, this._snap(next.z, this.scaleSnap)),
      );
      this.object.scale.copy(next);
    }
    this.update();
    this.dispatchEvent({ type: "change" });
    this.dispatchEvent({ type: "objectChange" });
  }

  _pointerUp(event) {
    if (!this.dragging) return;
    event.preventDefault();
    this.dragging = false;
    this.domElement.releasePointerCapture?.(event.pointerId);
    this.dispatchEvent({ type: "dragging-changed", value: false });
    this.dispatchEvent({ type: "objectChange" });
  }

  dispose() {
    this.domElement.removeEventListener("pointerdown", this._onPointerDown);
    this.domElement.removeEventListener("pointermove", this._onPointerMove);
    this.domElement.removeEventListener("pointerup", this._onPointerUp);
    this.domElement.removeEventListener("pointercancel", this._onPointerUp);
    this.traverse((object) => {
      object.geometry?.dispose();
      object.material?.dispose();
    });
  }
}

export { TransformControls };
