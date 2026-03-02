/**
 * Morpho Body Generator
 *
 * Converts agent body parameters into Three.js 3D objects.
 * Agents have FULL AUTONOMY — this module interprets, never restricts.
 *
 * Supported base_shape values:
 *   sphere, cube, torus, crystal, fluid, organic, fractal,
 *   cloud, flame, tree, custom (or any free text)
 */

const MorphoBodyGenerator = {

    generate(bodyParams, THREE) {
        const p = bodyParams || {};
        const group = new THREE.Group();

        // Parse parameters with defaults
        const shape = (p.base_shape || 'sphere').toLowerCase();
        const scale = Math.max(0.3, Math.min(3.0, p.scale || 1.0));
        const complexity = Math.max(0, Math.min(1, p.complexity || 0.5));
        const symmetry = p.symmetry || 0.8;
        const solidity = Math.max(0.1, p.solidity || 0.8);

        // Colors
        const primary = new THREE.Color(p.color_primary || '#4A90D9');
        const secondary = new THREE.Color(p.color_secondary || '#2ECC71');
        const emissiveColor = new THREE.Color(p.emissive_color || '#000000');
        const emissiveIntensity = Math.min(2, p.emissive_intensity || 0.3);

        // Material properties
        const materialProps = {
            color: primary,
            roughness: Math.max(0, Math.min(1, p.roughness || 0.5)),
            metalness: Math.max(0, Math.min(1, p.metallic || 0.0)),
            transparent: solidity < 0.95,
            opacity: Math.max(0.1, solidity),
            emissive: emissiveColor,
            emissiveIntensity: emissiveIntensity,
        };

        // Generate core body based on shape
        const coreMesh = this._generateShape(shape, scale, complexity, materialProps, THREE);
        group.add(coreMesh);

        // Add complexity layers
        if (complexity > 0.3) {
            const details = this._addComplexityDetails(shape, scale, complexity, secondary, materialProps, THREE);
            details.forEach(d => group.add(d));
        }

        // Add aura
        if ((p.aura_radius || 0) > 0.1) {
            const aura = this._createAura(p.aura_radius, p.aura_color || '#4A90D9', THREE);
            group.add(aura);
        }

        // Add particles
        if (p.particle_type && p.particle_type !== 'none') {
            const particles = this._createParticles(p, THREE);
            group.add(particles);
        }

        // Store params for animation
        group.userData.bodyParams = p;

        return group;
    },

    _generateShape(shape, scale, complexity, matProps, THREE) {
        const mat = new THREE.MeshStandardMaterial(matProps);
        let geo;

        switch (shape) {
            case 'sphere':
                geo = new THREE.SphereGeometry(
                    scale * 0.5,
                    Math.floor(16 + complexity * 32),
                    Math.floor(16 + complexity * 32)
                );
                break;

            case 'cube':
                geo = new THREE.BoxGeometry(
                    scale * 0.7, scale * 0.7, scale * 0.7,
                    Math.floor(1 + complexity * 4),
                    Math.floor(1 + complexity * 4),
                    Math.floor(1 + complexity * 4)
                );
                break;

            case 'torus':
                geo = new THREE.TorusGeometry(
                    scale * 0.4,
                    scale * 0.15,
                    Math.floor(8 + complexity * 24),
                    Math.floor(16 + complexity * 48)
                );
                break;

            case 'crystal': {
                // Octahedron-based crystal
                geo = new THREE.OctahedronGeometry(scale * 0.5, Math.floor(complexity * 3));
                // Stretch it vertically for crystal look
                const positions = geo.attributes.position;
                for (let i = 0; i < positions.count; i++) {
                    const y = positions.getY(i);
                    positions.setY(i, y * 1.5);
                }
                positions.needsUpdate = true;
                mat.metalness = Math.max(mat.metalness, 0.3);
                mat.roughness = Math.min(mat.roughness, 0.3);
                break;
            }

            case 'fluid': {
                // Distorted sphere
                geo = new THREE.SphereGeometry(scale * 0.5, 32, 32);
                const pos = geo.attributes.position;
                for (let i = 0; i < pos.count; i++) {
                    const v = new THREE.Vector3(pos.getX(i), pos.getY(i), pos.getZ(i));
                    const noise = Math.sin(v.x * 3) * Math.cos(v.y * 3) * Math.sin(v.z * 3) * 0.15 * complexity;
                    v.multiplyScalar(1 + noise);
                    pos.setXYZ(i, v.x, v.y, v.z);
                }
                pos.needsUpdate = true;
                geo.computeVertexNormals();
                mat.metalness = 0.6;
                mat.roughness = 0.1;
                break;
            }

            case 'organic': {
                // Soft blobby shape
                geo = new THREE.SphereGeometry(scale * 0.5, 24, 24);
                const orgPos = geo.attributes.position;
                for (let i = 0; i < orgPos.count; i++) {
                    const x = orgPos.getX(i), y = orgPos.getY(i), z = orgPos.getZ(i);
                    const dist = Math.sqrt(x*x + y*y + z*z);
                    const bump = Math.sin(x * 5) * Math.sin(y * 5) * Math.sin(z * 5) * 0.1 * complexity;
                    const factor = (dist + bump) / dist;
                    orgPos.setXYZ(i, x * factor, y * factor, z * factor);
                }
                orgPos.needsUpdate = true;
                geo.computeVertexNormals();
                break;
            }

            case 'fractal': {
                // Multi-scale octahedrons
                const mainGeo = new THREE.OctahedronGeometry(scale * 0.4, 1);
                const mesh = new THREE.Mesh(mainGeo, mat);
                const group = new THREE.Group();
                group.add(mesh);

                // Sub-octahedrons
                const subCount = Math.floor(4 + complexity * 8);
                for (let i = 0; i < subCount; i++) {
                    const subScale = 0.15 + Math.random() * 0.2;
                    const subGeo = new THREE.OctahedronGeometry(scale * subScale, 0);
                    const subMat = mat.clone();
                    subMat.opacity = Math.max(0.3, matProps.opacity - 0.2);
                    const subMesh = new THREE.Mesh(subGeo, subMat);
                    const angle = (i / subCount) * Math.PI * 2;
                    const r = scale * 0.4;
                    subMesh.position.set(
                        Math.cos(angle) * r * (0.8 + Math.random() * 0.4),
                        (Math.random() - 0.5) * r,
                        Math.sin(angle) * r * (0.8 + Math.random() * 0.4)
                    );
                    subMesh.rotation.set(Math.random(), Math.random(), Math.random());
                    group.add(subMesh);
                }
                return group;
            }

            case 'cloud': {
                // Cluster of transparent spheres
                const cloudGroup = new THREE.Group();
                const blobCount = Math.floor(5 + complexity * 10);
                for (let i = 0; i < blobCount; i++) {
                    const blobGeo = new THREE.SphereGeometry(scale * (0.15 + Math.random() * 0.25), 12, 12);
                    const blobMat = new THREE.MeshStandardMaterial({
                        ...matProps,
                        transparent: true,
                        opacity: 0.15 + Math.random() * 0.2,
                    });
                    const blob = new THREE.Mesh(blobGeo, blobMat);
                    blob.position.set(
                        (Math.random() - 0.5) * scale * 0.8,
                        (Math.random() - 0.5) * scale * 0.5,
                        (Math.random() - 0.5) * scale * 0.8
                    );
                    cloudGroup.add(blob);
                }
                return cloudGroup;
            }

            case 'flame': {
                // Cone + particles look
                const flameGroup = new THREE.Group();
                const coneGeo = new THREE.ConeGeometry(scale * 0.3, scale * 0.8, 8);
                const flameMat = new THREE.MeshStandardMaterial({
                    ...matProps,
                    emissive: new THREE.Color(matProps.color),
                    emissiveIntensity: 1.5,
                    transparent: true,
                    opacity: 0.7,
                });
                const cone = new THREE.Mesh(coneGeo, flameMat);
                flameGroup.add(cone);

                // Inner glow
                const innerGeo = new THREE.ConeGeometry(scale * 0.15, scale * 0.5, 6);
                const innerMat = new THREE.MeshBasicMaterial({
                    color: 0xffffff,
                    transparent: true,
                    opacity: 0.5,
                });
                const inner = new THREE.Mesh(innerGeo, innerMat);
                inner.position.y = -0.1;
                flameGroup.add(inner);

                return flameGroup;
            }

            case 'tree': {
                // Trunk + canopy
                const treeGroup = new THREE.Group();
                const trunkGeo = new THREE.CylinderGeometry(scale * 0.05, scale * 0.08, scale * 0.6, 8);
                const trunkMat = new THREE.MeshStandardMaterial({ color: 0x5c4033, roughness: 0.9 });
                const trunk = new THREE.Mesh(trunkGeo, trunkMat);
                trunk.position.y = -scale * 0.1;
                treeGroup.add(trunk);

                const canopyGeo = new THREE.IcosahedronGeometry(scale * 0.4, Math.floor(1 + complexity * 2));
                const canopy = new THREE.Mesh(canopyGeo, mat);
                canopy.position.y = scale * 0.3;
                treeGroup.add(canopy);

                return treeGroup;
            }

            default:
                // Unknown/custom shape — create something unique from the name
                geo = new THREE.IcosahedronGeometry(scale * 0.5, Math.floor(1 + complexity * 3));
                break;
        }

        const mesh = new THREE.Mesh(geo, mat);
        mesh.castShadow = true;
        return mesh;
    },

    _addComplexityDetails(shape, scale, complexity, secondaryColor, matProps, THREE) {
        const details = [];
        const detailCount = Math.floor(complexity * 6);

        for (let i = 0; i < detailCount; i++) {
            const size = scale * 0.05 * (1 + Math.random());
            const geo = new THREE.SphereGeometry(size, 8, 8);
            const mat = new THREE.MeshStandardMaterial({
                color: secondaryColor,
                emissive: secondaryColor,
                emissiveIntensity: 0.5,
                transparent: true,
                opacity: 0.6,
            });
            const mesh = new THREE.Mesh(geo, mat);
            const angle = (i / detailCount) * Math.PI * 2;
            const radius = scale * 0.35;
            mesh.position.set(
                Math.cos(angle) * radius,
                (Math.random() - 0.5) * scale * 0.5,
                Math.sin(angle) * radius
            );
            details.push(mesh);
        }

        return details;
    },

    _createAura(radius, color, THREE) {
        const auraGeo = new THREE.SphereGeometry(radius, 16, 16);
        const auraMat = new THREE.MeshBasicMaterial({
            color: new THREE.Color(color),
            transparent: true,
            opacity: 0.08,
            side: THREE.BackSide,
        });
        return new THREE.Mesh(auraGeo, auraMat);
    },

    _createParticles(params, THREE) {
        const count = Math.floor((params.particle_density || 0.3) * 80);
        const radius = (params.aura_radius || 1) * 1.5;
        const color = new THREE.Color(params.particle_color || '#FFFFFF');

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
        points.userData.particleType = params.particle_type;
        return points;
    },
};

// Make globally available
if (typeof window !== 'undefined') {
    window.MorphoBodyGenerator = MorphoBodyGenerator;
}
