/**
 * Morpho Body Builder — CAD-based body renderer
 *
 * Converts a part tree (from the /build endpoint) into Three.js scene objects.
 * Supports: primitives, custom meshes, extrusions, revolves, joints, and materials.
 *
 * SolidWorks-like workflow: Drawing → Parts → Assembly
 */

const MorphoBodyBuilder = {

    /**
     * Build a Three.js Group from a part tree.
     * @param {object} partTree - { version, parts, joints, motions, idle_motion, aura, particles }
     * @param {object} THREE - Three.js namespace
     * @returns {THREE.Group}
     */
    build(partTree, THREE) {
        const group = new THREE.Group();
        const partMeshes = {};  // part_id → THREE.Mesh or THREE.Group

        if (!partTree || !partTree.parts) return group;

        // Phase 1: Create all part meshes
        for (const [partId, part] of Object.entries(partTree.parts)) {
            const mesh = this._createPart(part, THREE);
            if (!mesh) continue;

            // Apply transform
            if (part.position) mesh.position.set(...part.position);
            if (part.rotation) mesh.rotation.set(...part.rotation);
            if (part.scale) mesh.scale.set(...part.scale);

            // Apply material
            if (part.material) {
                this._applyMaterial(mesh, part.material, THREE);
            } else {
                // Default material
                this._applyMaterial(mesh, {
                    color: '#4A90D9',
                    roughness: 0.5,
                    metalness: 0.1,
                    opacity: 1.0,
                    emissive_color: '#000000',
                    emissive_intensity: 0.0,
                }, THREE);
            }

            mesh.userData.partId = partId;
            mesh.castShadow = true;
            partMeshes[partId] = mesh;
            group.add(mesh);
        }

        // Phase 2: Process joints — create pivot hierarchies
        if (partTree.joints) {
            for (const [jointId, joint] of Object.entries(partTree.joints)) {
                const meshA = partMeshes[joint.part_a];
                const meshB = partMeshes[joint.part_b];
                if (!meshA || !meshB) continue;

                // Create a pivot point at the joint anchor
                const pivot = new THREE.Group();
                pivot.position.set(...(joint.anchor || [0, 0, 0]));
                pivot.userData.jointId = jointId;
                pivot.userData.jointType = joint.type;
                pivot.userData.jointAxis = joint.axis || [0, 1, 0];
                pivot.userData.jointLimits = joint.limits || null;

                // Reparent meshB under the pivot
                // Offset meshB's position relative to the pivot
                const worldPosB = meshB.position.clone();
                const anchorVec = new THREE.Vector3(...(joint.anchor || [0, 0, 0]));
                meshB.position.sub(anchorVec);

                group.remove(meshB);
                pivot.add(meshB);
                group.add(pivot);

                // Store pivot for animation
                partMeshes[`_pivot_${jointId}`] = pivot;
            }
        }

        // Phase 3: Aura
        if (partTree.aura) {
            const aura = this._createAura(partTree.aura, THREE);
            group.add(aura);
        }

        // Phase 4: Particles
        if (partTree.particles) {
            const particles = this._createParticles(partTree.particles, THREE);
            group.add(particles);
        }

        // Store part tree data for animator
        group.userData.partTree = partTree;
        group.userData.partMeshes = partMeshes;

        return group;
    },

    /**
     * Create a Three.js mesh from a part definition.
     */
    _createPart(part, THREE) {
        switch (part.type) {
            case 'primitive':
                return this._createPrimitive(part, THREE);
            case 'mesh':
                return this._createCustomMesh(part, THREE);
            case 'extrude':
                return this._createExtrusion(part, THREE);
            case 'revolve':
                return this._createRevolve(part, THREE);
            case 'boolean':
                return this._createBoolean(part, THREE);
            default:
                return null;
        }
    },

    /**
     * Create a primitive geometry.
     */
    _createPrimitive(part, THREE) {
        const size = part.size || {};
        let geo;

        switch (part.primitive_type) {
            case 'sphere':
                geo = new THREE.SphereGeometry(size.radius || 0.5, 32, 32);
                break;
            case 'box':
                geo = new THREE.BoxGeometry(
                    size.width || 1, size.height || 1, size.depth || 1
                );
                break;
            case 'cylinder':
                geo = new THREE.CylinderGeometry(
                    size.radius || 0.5, size.radius || 0.5,
                    size.height || 1, 32
                );
                break;
            case 'cone':
                geo = new THREE.ConeGeometry(
                    size.radius || 0.5, size.height || 1, 32
                );
                break;
            case 'torus':
                geo = new THREE.TorusGeometry(
                    size.radius || 0.5, size.tube || 0.15, 16, 48
                );
                break;
            case 'plane':
                geo = new THREE.PlaneGeometry(
                    size.width || 1, size.height || 1
                );
                break;
            default:
                geo = new THREE.SphereGeometry(0.5, 32, 32);
        }

        // Apply features (fillet, chamfer, shell, hole, pattern)
        if (part._features) {
            // Features are visual approximations in Three.js
            // Real CSG would need a library like three-bvh-csg
            for (const feature of part._features) {
                if (feature.type === 'hole') {
                    // Approximate: we note it for the frontend but can't do true CSG without a library
                    // Store for potential future CSG implementation
                }
            }
        }

        const mat = new THREE.MeshStandardMaterial({ color: 0x4A90D9 });
        const mesh = new THREE.Mesh(geo, mat);
        mesh.castShadow = true;
        return mesh;
    },

    /**
     * Create a mesh from raw vertex/face data.
     */
    _createCustomMesh(part, THREE) {
        const vertices = part.vertices || [];
        const faces = part.faces || [];

        if (vertices.length < 3 || faces.length < 1) return null;

        const geo = new THREE.BufferGeometry();

        // Vertices
        const positions = new Float32Array(faces.length * 3 * 3);
        let idx = 0;
        for (const face of faces) {
            for (const vi of face) {
                if (vi < vertices.length) {
                    positions[idx++] = vertices[vi][0];
                    positions[idx++] = vertices[vi][1];
                    positions[idx++] = vertices[vi][2];
                }
            }
        }
        geo.setAttribute('position', new THREE.BufferAttribute(positions.slice(0, idx), 3));
        geo.computeVertexNormals();

        const mat = new THREE.MeshStandardMaterial({
            color: 0x4A90D9,
            side: THREE.DoubleSide,
        });

        return new THREE.Mesh(geo, mat);
    },

    /**
     * Create an extrusion from a sketch profile.
     */
    _createExtrusion(part, THREE) {
        const sketch = part.sketch;
        if (!sketch || !sketch.curves || sketch.curves.length === 0) {
            // Fallback: simple box
            return this._createPrimitive({
                primitive_type: 'box',
                size: { width: 1, height: part.depth || 1, depth: 1 },
            }, THREE);
        }

        const shape = this._sketchToShape(sketch, THREE);
        if (!shape) {
            return this._createPrimitive({
                primitive_type: 'box',
                size: { width: 1, height: part.depth || 1, depth: 1 },
            }, THREE);
        }

        const extrudeSettings = {
            depth: part.depth || 1,
            bevelEnabled: false,
        };

        const geo = new THREE.ExtrudeGeometry(shape, extrudeSettings);
        const mat = new THREE.MeshStandardMaterial({ color: 0x4A90D9 });
        return new THREE.Mesh(geo, mat);
    },

    /**
     * Create a revolve (lathe) from a sketch profile.
     */
    _createRevolve(part, THREE) {
        const sketch = part.sketch;
        if (!sketch || !sketch.curves || sketch.curves.length === 0) {
            // Fallback: torus
            return this._createPrimitive({
                primitive_type: 'torus',
                size: { radius: 0.5, tube: 0.15 },
            }, THREE);
        }

        // Extract points from sketch for lathe
        const points = this._sketchToLathePoints(sketch, THREE);
        if (points.length < 2) {
            return this._createPrimitive({
                primitive_type: 'sphere',
                size: { radius: 0.5 },
            }, THREE);
        }

        const segments = 32;
        const angle = part.angle || Math.PI * 2;
        const geo = new THREE.LatheGeometry(points, segments, 0, angle);
        const mat = new THREE.MeshStandardMaterial({ color: 0x4A90D9 });
        return new THREE.Mesh(geo, mat);
    },

    /**
     * Create a boolean combination of two parts.
     */
    _createBoolean(part, THREE) {
        // True CSG requires three-bvh-csg or similar library
        // For now, render both parts as a group
        const group = new THREE.Group();
        const meshA = this._createPart(part.part_a, THREE);
        const meshB = this._createPart(part.part_b, THREE);
        if (meshA) group.add(meshA);
        if (meshB) {
            if (part.operation === 'subtract') {
                // Visual hint: make subtracted part wireframe
                meshB.traverse(child => {
                    if (child.material) {
                        child.material.wireframe = true;
                        child.material.opacity = 0.3;
                        child.material.transparent = true;
                    }
                });
            }
            group.add(meshB);
        }
        return group;
    },

    /**
     * Convert sketch curves into a THREE.Shape for extrusion.
     */
    _sketchToShape(sketch, THREE) {
        const shape = new THREE.Shape();
        let started = false;

        for (const curve of sketch.curves) {
            switch (curve.type) {
                case 'circle': {
                    const cx = curve.center[0];
                    const cy = curve.center[1];
                    const r = curve.radius;
                    // Create a circle path
                    const circleShape = new THREE.Shape();
                    circleShape.absarc(cx, cy, r, 0, Math.PI * 2, false);
                    return circleShape;
                }

                case 'rectangle': {
                    const x1 = curve.corner1[0], y1 = curve.corner1[1];
                    const x2 = curve.corner2[0], y2 = curve.corner2[1];
                    const rectShape = new THREE.Shape();
                    rectShape.moveTo(x1, y1);
                    rectShape.lineTo(x2, y1);
                    rectShape.lineTo(x2, y2);
                    rectShape.lineTo(x1, y2);
                    rectShape.lineTo(x1, y1);
                    return rectShape;
                }

                case 'polygon': {
                    const cx2 = curve.center[0];
                    const cy2 = curve.center[1];
                    const r2 = curve.radius;
                    const sides = curve.sides || 6;
                    const polyShape = new THREE.Shape();
                    for (let i = 0; i <= sides; i++) {
                        const angle = (i / sides) * Math.PI * 2;
                        const px = cx2 + r2 * Math.cos(angle);
                        const py = cy2 + r2 * Math.sin(angle);
                        if (i === 0) polyShape.moveTo(px, py);
                        else polyShape.lineTo(px, py);
                    }
                    return polyShape;
                }

                case 'line':
                    if (!started) {
                        shape.moveTo(curve.from[0], curve.from[1]);
                        started = true;
                    }
                    shape.lineTo(curve.to[0], curve.to[1]);
                    break;

                case 'arc': {
                    const acx = curve.center[0];
                    const acy = curve.center[1];
                    const ar = curve.radius;
                    if (!started) {
                        const sx = acx + ar * Math.cos(curve.start_angle);
                        const sy = acy + ar * Math.sin(curve.start_angle);
                        shape.moveTo(sx, sy);
                        started = true;
                    }
                    shape.absarc(acx, acy, ar, curve.start_angle, curve.end_angle, false);
                    break;
                }

                case 'spline':
                    if (curve.points && curve.points.length >= 2) {
                        const splinePoints = curve.points.map(p => new THREE.Vector2(p[0], p[1]));
                        if (!started) {
                            shape.moveTo(splinePoints[0].x, splinePoints[0].y);
                            started = true;
                        }
                        shape.splineThru(splinePoints.slice(1));
                    }
                    break;
            }
        }

        return started ? shape : null;
    },

    /**
     * Convert sketch curves into Vector2 points for lathe geometry (revolve).
     */
    _sketchToLathePoints(sketch, THREE) {
        const points = [];

        for (const curve of sketch.curves) {
            switch (curve.type) {
                case 'line':
                    if (points.length === 0) {
                        points.push(new THREE.Vector2(
                            Math.abs(curve.from[0]),  // Lathe uses distance from axis
                            curve.from[1]
                        ));
                    }
                    points.push(new THREE.Vector2(
                        Math.abs(curve.to[0]),
                        curve.to[1]
                    ));
                    break;

                case 'spline':
                    if (curve.points) {
                        for (const p of curve.points) {
                            points.push(new THREE.Vector2(Math.abs(p[0]), p[1]));
                        }
                    }
                    break;

                case 'arc': {
                    const steps = 16;
                    const startA = curve.start_angle || 0;
                    const endA = curve.end_angle || Math.PI * 2;
                    for (let i = 0; i <= steps; i++) {
                        const t = startA + (endA - startA) * (i / steps);
                        const px = curve.center[0] + curve.radius * Math.cos(t);
                        const py = curve.center[1] + curve.radius * Math.sin(t);
                        points.push(new THREE.Vector2(Math.abs(px), py));
                    }
                    break;
                }
            }
        }

        return points;
    },

    /**
     * Apply material properties to a mesh.
     */
    _applyMaterial(mesh, matDef, THREE) {
        const props = {
            color: new THREE.Color(matDef.color || '#4A90D9'),
            roughness: matDef.roughness !== undefined ? matDef.roughness : 0.5,
            metalness: matDef.metalness !== undefined ? matDef.metalness : 0.1,
            transparent: (matDef.opacity || 1) < 0.95,
            opacity: matDef.opacity || 1.0,
            emissive: new THREE.Color(matDef.emissive_color || '#000000'),
            emissiveIntensity: matDef.emissive_intensity || 0,
        };

        const material = new THREE.MeshStandardMaterial(props);

        mesh.traverse(child => {
            if (child.isMesh) {
                if (child.material) child.material.dispose();
                child.material = material.clone();
            }
        });
    },

    /**
     * Create an aura sphere.
     */
    _createAura(auraDef, THREE) {
        const geo = new THREE.SphereGeometry(auraDef.radius || 1, 16, 16);
        const mat = new THREE.MeshBasicMaterial({
            color: new THREE.Color(auraDef.color || '#4A90D9'),
            transparent: true,
            opacity: auraDef.opacity || 0.08,
            side: THREE.BackSide,
        });
        const mesh = new THREE.Mesh(geo, mat);
        mesh.userData.isAura = true;
        return mesh;
    },

    /**
     * Create particle system.
     */
    _createParticles(particleDef, THREE) {
        const count = Math.floor((particleDef.density || 0.3) * 80);
        const radius = particleDef.radius || 1.5;
        const color = new THREE.Color(particleDef.color || '#FFFFFF');

        const geo = new THREE.BufferGeometry();
        const positions = new Float32Array(count * 3);
        for (let i = 0; i < count * 3; i += 3) {
            const theta = Math.random() * Math.PI * 2;
            const phi = Math.random() * Math.PI;
            const r = Math.random() * radius;
            positions[i] = r * Math.sin(phi) * Math.cos(theta);
            positions[i + 1] = r * Math.sin(phi) * Math.sin(theta);
            positions[i + 2] = r * Math.cos(phi);
        }
        geo.setAttribute('position', new THREE.BufferAttribute(positions, 3));

        const mat = new THREE.PointsMaterial({
            color: color,
            size: 0.05,
            transparent: true,
            opacity: 0.6,
        });

        const points = new THREE.Points(geo, mat);
        points.userData.isParticle = true;
        points.userData.particleType = particleDef.type || 'dust';
        return points;
    },
};

// Make globally available
if (typeof window !== 'undefined') {
    window.MorphoBodyBuilder = MorphoBodyBuilder;
}
