/**
 * Morpho Agent Animator
 *
 * Animates agent bodies based on their parameters and current state.
 * Supports both legacy (single-mesh) and CAD (joint-based) bodies.
 * Each agent has its own animation rhythm — no two agents move the same.
 */

class MorphoAgentAnimator {
    constructor(group, bodyParams) {
        this.group = group;
        this.params = bodyParams || {};
        this.state = 'idle';
        this.energy = 0.5;
        this.birthTime = performance.now() / 1000;

        // Detect if this is a CAD body (v2)
        this.isCAD = (this.params.version === 2);

        // Animation properties
        if (this.isCAD) {
            const idle = this.params.idle_motion || {};
            this.idlePattern = (idle.pattern || 'float').toLowerCase();
            this.speed = Math.max(0.1, Math.min(5.0, idle.speed || 0.5));
            this.amplitude = Math.max(0, Math.min(2.0, idle.amplitude || 0.3));

            // Joint motions
            this.jointMotions = this.params.motions || {};
            this._collectPivots();
        } else {
            this.idlePattern = (this.params.idle_pattern || 'float').toLowerCase();
            this.speed = Math.max(0.1, Math.min(2.0, this.params.speed || 0.5));
            this.amplitude = Math.max(0, Math.min(1.0, this.params.amplitude || 0.3));
        }

        // Unique phase offset so agents aren't synchronized
        this.phaseOffset = Math.random() * Math.PI * 2;

        // Trail
        this.trail = this.params.trail || false;
        this.trailPositions = [];

        // State-driven animation overrides
        this.stateIntensity = 1.0;
        this.targetStateIntensity = 1.0;
    }

    /**
     * Collect pivot groups (joints) from the scene graph for animation.
     */
    _collectPivots() {
        this.pivots = {};
        this.group.traverse(child => {
            if (child.userData && child.userData.jointId) {
                this.pivots[child.userData.jointId] = child;
            }
        });
    }

    setState(newState, energy) {
        this.state = newState || 'idle';
        this.energy = Math.max(0, Math.min(1, energy || 0.5));

        switch (this.state) {
            case 'thinking':
                this.targetStateIntensity = 0.5;
                break;
            case 'working':
                this.targetStateIntensity = 1.2;
                break;
            case 'excited':
                this.targetStateIntensity = 2.0;
                break;
            case 'social':
                this.targetStateIntensity = 1.5;
                break;
            case 'error':
                this.targetStateIntensity = 0.3;
                break;
            default:
                this.targetStateIntensity = 1.0;
        }
    }

    update(elapsed, delta) {
        const t = elapsed + this.phaseOffset;
        const sp = this.speed;
        const amp = this.amplitude;

        // Smooth state intensity transition
        this.stateIntensity += (this.targetStateIntensity - this.stateIntensity) * 0.05;
        const si = this.stateIntensity;

        // ─── Idle Pattern Animations ───
        this._applyIdlePattern(t, sp, amp, si);

        // ─── Joint Animations (CAD bodies) ───
        if (this.isCAD) {
            this._applyJointMotions(t, si);
        }

        // ─── State-driven visual effects ───
        this._applyStateEffects(t, si);

        // ─── Particle animation ───
        this._animateParticles(t, sp);

        // ─── Aura pulse ───
        this._animateAura(t, sp, si);
    }

    /**
     * Apply motion patterns to joints (CAD bodies).
     */
    _applyJointMotions(t, intensity) {
        for (const [jointId, motion] of Object.entries(this.jointMotions)) {
            const pivot = this.pivots[jointId];
            if (!pivot) continue;

            const axis = pivot.userData.jointAxis || [0, 1, 0];
            const speed = motion.speed || 1.0;
            const amplitude = motion.amplitude || 0.5;
            const phase = motion.phase_offset || 0;
            const limits = pivot.userData.jointLimits;

            let angle = 0;

            switch (motion.pattern) {
                case 'oscillate':
                    angle = Math.sin(t * speed + phase) * amplitude * intensity;
                    break;
                case 'rotate':
                    angle = (t * speed + phase) * intensity;
                    break;
                case 'bounce':
                    angle = Math.abs(Math.sin(t * speed + phase)) * amplitude * intensity;
                    break;
                default:
                    angle = Math.sin(t * speed + phase) * amplitude * 0.5 * intensity;
            }

            // Apply limits
            if (limits) {
                if (limits.min !== undefined) angle = Math.max(limits.min, angle);
                if (limits.max !== undefined) angle = Math.min(limits.max, angle);
            }

            // Apply rotation around the joint axis
            if (axis[0] > 0.5) pivot.rotation.x = angle;
            else if (axis[1] > 0.5) pivot.rotation.y = angle;
            else if (axis[2] > 0.5) pivot.rotation.z = angle;
            else {
                // Arbitrary axis — default to Y
                pivot.rotation.y = angle;
            }
        }
    }

    _applyIdlePattern(t, speed, amplitude, intensity) {
        const group = this.group;

        switch (this.idlePattern) {
            case 'float':
                group.position.y += Math.sin(t * speed * 1.5) * amplitude * 0.003 * intensity;
                group.rotation.y += 0.002 * speed * intensity;
                break;

            case 'spin':
                group.rotation.y += 0.02 * speed * intensity;
                group.rotation.x = Math.sin(t * speed * 0.5) * 0.1 * amplitude;
                break;

            case 'pulse': {
                const pulseScale = 1 + Math.sin(t * speed * 2) * amplitude * 0.15 * intensity;
                group.scale.setScalar(pulseScale);
                break;
            }

            case 'wave':
                group.position.y += Math.sin(t * speed * 2) * amplitude * 0.005 * intensity;
                group.rotation.z = Math.sin(t * speed) * amplitude * 0.2 * intensity;
                break;

            case 'orbit': {
                const orbitR = amplitude * 0.3 * intensity;
                group.position.x += Math.cos(t * speed * 1.5) * orbitR * 0.005;
                group.position.z += Math.sin(t * speed * 1.5) * orbitR * 0.005;
                group.rotation.y += 0.01 * speed;
                break;
            }

            case 'breathe': {
                const breathe = 1 + Math.sin(t * speed * 0.8) * amplitude * 0.1 * intensity;
                group.scale.set(breathe, breathe * 1.05, breathe);
                break;
            }

            case 'flicker': {
                // Random opacity flicker
                group.traverse(child => {
                    if (child.material && child.material.opacity !== undefined) {
                        const baseOpacity = this.params.opacity || 0.9;
                        child.material.opacity = baseOpacity * (0.7 + Math.random() * 0.3 * intensity);
                    }
                });
                break;
            }

            case 'still':
                // Minimal movement — just very slow rotation
                group.rotation.y += 0.0005 * speed;
                break;

            default:
                // Custom or unknown — gentle float
                group.position.y += Math.sin(t * speed) * amplitude * 0.002 * intensity;
                group.rotation.y += 0.001 * speed;
                break;
        }
    }

    _applyStateEffects(t, intensity) {
        const group = this.group;

        switch (this.state) {
            case 'thinking':
                // Slow pulse, dimmer
                group.traverse(child => {
                    if (child.material && child.material.emissiveIntensity !== undefined) {
                        child.material.emissiveIntensity = 0.1 + Math.sin(t * 0.5) * 0.1;
                    }
                });
                break;

            case 'excited':
                // Fast pulse, brighter
                group.traverse(child => {
                    if (child.material && child.material.emissiveIntensity !== undefined) {
                        child.material.emissiveIntensity = 0.5 + Math.sin(t * 4) * 0.5;
                    }
                });
                // Extra jitter
                group.position.x += (Math.random() - 0.5) * 0.01 * intensity;
                group.position.z += (Math.random() - 0.5) * 0.01 * intensity;
                break;

            case 'social':
                // Slight lean toward focus target (visual only)
                group.rotation.z = Math.sin(t * 2) * 0.05 * intensity;
                break;

            case 'error':
                // Red flash
                group.traverse(child => {
                    if (child.material && child.material.emissive) {
                        const flash = Math.sin(t * 6) > 0 ? 0.5 : 0;
                        child.material.emissive.setRGB(flash, 0, 0);
                    }
                });
                break;

            case 'working':
                // Steady bright glow
                group.traverse(child => {
                    if (child.material && child.material.emissiveIntensity !== undefined) {
                        child.material.emissiveIntensity = 0.4 + this.energy * 0.6;
                    }
                });
                break;
        }
    }

    _animateParticles(t, speed) {
        this.group.traverse(child => {
            if (child.isPoints && child.userData.isParticle) {
                const type = child.userData.particleType;
                const positions = child.geometry.attributes.position;

                switch (type) {
                    case 'sparks':
                        for (let i = 0; i < positions.count; i++) {
                            positions.setY(i, positions.getY(i) + Math.sin(t * speed * 3 + i) * 0.005);
                        }
                        positions.needsUpdate = true;
                        break;

                    case 'fireflies':
                        for (let i = 0; i < positions.count; i++) {
                            const phase = i * 1.7;
                            positions.setX(i, positions.getX(i) + Math.sin(t * speed + phase) * 0.003);
                            positions.setY(i, positions.getY(i) + Math.cos(t * speed * 0.7 + phase) * 0.003);
                            positions.setZ(i, positions.getZ(i) + Math.sin(t * speed * 0.5 + phase) * 0.003);
                        }
                        positions.needsUpdate = true;
                        break;

                    case 'dust':
                    case 'smoke':
                        child.rotation.y += 0.002 * speed;
                        break;

                    case 'data':
                        // Matrix-like rising
                        for (let i = 0; i < positions.count; i++) {
                            let y = positions.getY(i) + 0.01 * speed;
                            if (y > 2) y = -2;
                            positions.setY(i, y);
                        }
                        positions.needsUpdate = true;
                        break;

                    default:
                        // Gentle rotation
                        child.rotation.y += 0.001 * speed;
                        break;
                }
            }
        });
    }

    _animateAura(t, speed, intensity) {
        this.group.traverse(child => {
            if (child.material && child.material.side === 1) { // BackSide = aura
                const baseOpacity = 0.08;
                child.material.opacity = baseOpacity + Math.sin(t * speed) * 0.03 * intensity;
                child.scale.setScalar(1 + Math.sin(t * speed * 0.5) * 0.05 * intensity);
            }
        });
    }
}

// Make globally available
if (typeof window !== 'undefined') {
    window.MorphoAgentAnimator = MorphoAgentAnimator;
}
