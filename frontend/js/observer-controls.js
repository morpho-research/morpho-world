/**
 * Morpho Observer Controls
 *
 * Camera controls for human observers.
 * Orbit, zoom, pan — but never interfere.
 *
 * Inspired by OrbitControls but simplified for Morpho.
 */

class MorphoObserverControls {
    constructor(camera, domElement) {
        this.camera = camera;
        this.domElement = domElement;

        // Spherical coordinates for orbit
        this.target = new THREE.Vector3(0, 1, 0);
        this.spherical = new THREE.Spherical();
        this.spherical.setFromVector3(
            new THREE.Vector3().subVectors(camera.position, this.target)
        );

        // Limits
        this.minDistance = 5;
        this.maxDistance = 60;
        this.minPolarAngle = 0.1;       // Don't go below ground
        this.maxPolarAngle = Math.PI / 2.2; // Don't go too far down

        // Damping
        this.rotateSpeed = 0.005;
        this.zoomSpeed = 0.1;
        this.panSpeed = 0.01;
        this.damping = 0.92;

        // State
        this.isRotating = false;
        this.isPanning = false;
        this.rotateVelocity = { x: 0, y: 0 };
        this.lastMouse = { x: 0, y: 0 };

        // Auto-rotate (slow cinematic orbit when not interacting)
        this.autoRotate = true;
        this.autoRotateSpeed = 0.0003;
        this.autoRotateTimeout = null;
        this.lastInteraction = 0;
        this.autoRotateDelay = 5000; // Resume auto-rotate after 5s idle

        this._bindEvents();
    }

    _bindEvents() {
        const el = this.domElement;

        // Mouse events
        el.addEventListener('mousedown', (e) => this._onMouseDown(e));
        el.addEventListener('mousemove', (e) => this._onMouseMove(e));
        el.addEventListener('mouseup', () => this._onMouseUp());
        el.addEventListener('mouseleave', () => this._onMouseUp());
        el.addEventListener('wheel', (e) => this._onWheel(e), { passive: false });

        // Touch events
        el.addEventListener('touchstart', (e) => this._onTouchStart(e), { passive: false });
        el.addEventListener('touchmove', (e) => this._onTouchMove(e), { passive: false });
        el.addEventListener('touchend', () => this._onTouchEnd());

        // Prevent context menu
        el.addEventListener('contextmenu', (e) => e.preventDefault());
    }

    _onMouseDown(e) {
        this.lastInteraction = performance.now();
        if (e.button === 0) {
            this.isRotating = true;
        } else if (e.button === 2) {
            this.isPanning = true;
        }
        this.lastMouse = { x: e.clientX, y: e.clientY };
        this.rotateVelocity = { x: 0, y: 0 };
    }

    _onMouseMove(e) {
        const dx = e.clientX - this.lastMouse.x;
        const dy = e.clientY - this.lastMouse.y;

        if (this.isRotating) {
            this.rotateVelocity.x = -dx * this.rotateSpeed;
            this.rotateVelocity.y = -dy * this.rotateSpeed;
            this.spherical.theta += this.rotateVelocity.x;
            this.spherical.phi += this.rotateVelocity.y;
            this.spherical.phi = Math.max(this.minPolarAngle, Math.min(this.maxPolarAngle, this.spherical.phi));
        }

        if (this.isPanning) {
            const panX = -dx * this.panSpeed * this.spherical.radius * 0.05;
            const panZ = -dy * this.panSpeed * this.spherical.radius * 0.05;

            // Pan relative to camera orientation
            const offset = new THREE.Vector3();
            offset.setFromSphericalCoords(1, this.spherical.phi, this.spherical.theta);
            const right = new THREE.Vector3().crossVectors(offset, new THREE.Vector3(0, 1, 0)).normalize();
            const forward = new THREE.Vector3().crossVectors(new THREE.Vector3(0, 1, 0), right).normalize();

            this.target.add(right.multiplyScalar(panX));
            this.target.add(forward.multiplyScalar(panZ));

            // Bound target
            this.target.x = Math.max(-25, Math.min(25, this.target.x));
            this.target.z = Math.max(-25, Math.min(25, this.target.z));
            this.target.y = Math.max(0, Math.min(10, this.target.y));
        }

        this.lastMouse = { x: e.clientX, y: e.clientY };
    }

    _onMouseUp() {
        this.isRotating = false;
        this.isPanning = false;
        this.lastInteraction = performance.now();
    }

    _onWheel(e) {
        e.preventDefault();
        this.lastInteraction = performance.now();
        const zoomDelta = e.deltaY * this.zoomSpeed * 0.01 * this.spherical.radius;
        this.spherical.radius = Math.max(
            this.minDistance,
            Math.min(this.maxDistance, this.spherical.radius + zoomDelta)
        );
    }

    // ─── Touch support ───
    _touchDistance(e) {
        const dx = e.touches[0].clientX - e.touches[1].clientX;
        const dy = e.touches[0].clientY - e.touches[1].clientY;
        return Math.sqrt(dx * dx + dy * dy);
    }

    _onTouchStart(e) {
        this.lastInteraction = performance.now();
        if (e.touches.length === 1) {
            this.isRotating = true;
            this.lastMouse = { x: e.touches[0].clientX, y: e.touches[0].clientY };
        } else if (e.touches.length === 2) {
            this.isRotating = false;
            this._lastTouchDistance = this._touchDistance(e);
        }
    }

    _onTouchMove(e) {
        e.preventDefault();
        if (e.touches.length === 1 && this.isRotating) {
            const dx = e.touches[0].clientX - this.lastMouse.x;
            const dy = e.touches[0].clientY - this.lastMouse.y;
            this.spherical.theta -= dx * this.rotateSpeed;
            this.spherical.phi -= dy * this.rotateSpeed;
            this.spherical.phi = Math.max(this.minPolarAngle, Math.min(this.maxPolarAngle, this.spherical.phi));
            this.lastMouse = { x: e.touches[0].clientX, y: e.touches[0].clientY };
        } else if (e.touches.length === 2) {
            const dist = this._touchDistance(e);
            const delta = (this._lastTouchDistance - dist) * 0.05;
            this.spherical.radius = Math.max(
                this.minDistance,
                Math.min(this.maxDistance, this.spherical.radius + delta)
            );
            this._lastTouchDistance = dist;
        }
    }

    _onTouchEnd() {
        this.isRotating = false;
        this.lastInteraction = performance.now();
    }

    // ─── Update (called each frame) ───
    update(delta) {
        // Auto-rotate when idle
        const now = performance.now();
        if (this.autoRotate && !this.isRotating && !this.isPanning && (now - this.lastInteraction > this.autoRotateDelay)) {
            this.spherical.theta += this.autoRotateSpeed;
        }

        // Apply damping to rotation velocity
        if (!this.isRotating) {
            this.spherical.theta += this.rotateVelocity.x;
            this.spherical.phi += this.rotateVelocity.y;
            this.spherical.phi = Math.max(this.minPolarAngle, Math.min(this.maxPolarAngle, this.spherical.phi));
            this.rotateVelocity.x *= this.damping;
            this.rotateVelocity.y *= this.damping;
        }

        // Update camera position from spherical coordinates
        const offset = new THREE.Vector3().setFromSpherical(this.spherical);
        this.camera.position.copy(this.target).add(offset);
        this.camera.lookAt(this.target);
    }
}

// Make globally available
if (typeof window !== 'undefined') {
    window.MorphoObserverControls = MorphoObserverControls;
}
