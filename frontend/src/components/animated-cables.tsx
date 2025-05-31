"use client"

import { useEffect, useRef, useMemo } from "react"

interface Cable {
  id: number
  path: string
  delay: number
  duration: number
  color: string
}

export function AnimatedCables() {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  // Generate cable paths from different sides of the screen to the center
  const cables: Cable[] = useMemo(() => [
    // Top cables
    {
      id: 1,
      path: "M 10% 0%, 30% 30%, 50% 50%",
      delay: 0,
      duration: 3,
      color: "rgba(100, 220, 255, 0.6)",
    },
    {
      id: 2,
      path: "M 30% 0%, 40% 25%, 50% 50%",
      delay: 0.5,
      duration: 2.5,
      color: "rgba(100, 220, 255, 0.5)",
    },
    {
      id: 3,
      path: "M 50% 0%, 50% 25%, 50% 50%",
      delay: 1,
      duration: 2,
      color: "rgba(100, 220, 255, 0.7)",
    },
    {
      id: 4,
      path: "M 70% 0%, 60% 25%, 50% 50%",
      delay: 1.5,
      duration: 2.5,
      color: "rgba(100, 220, 255, 0.5)",
    },
    {
      id: 5,
      path: "M 90% 0%, 70% 30%, 50% 50%",
      delay: 2,
      duration: 3,
      color: "rgba(100, 220, 255, 0.6)",
    },

    // Left cables
    {
      id: 6,
      path: "M 0% 20%, 25% 35%, 50% 50%",
      delay: 0.2,
      duration: 2.8,
      color: "rgba(100, 220, 255, 0.5)",
    },
    {
      id: 7,
      path: "M 0% 40%, 25% 45%, 50% 50%",
      delay: 0.7,
      duration: 2.3,
      color: "rgba(100, 220, 255, 0.6)",
    },
    {
      id: 8,
      path: "M 0% 60%, 25% 55%, 50% 50%",
      delay: 1.2,
      duration: 2.3,
      color: "rgba(100, 220, 255, 0.6)",
    },
    {
      id: 9,
      path: "M 0% 80%, 25% 65%, 50% 50%",
      delay: 1.7,
      duration: 2.8,
      color: "rgba(100, 220, 255, 0.5)",
    },

    // Right cables
    {
      id: 10,
      path: "M 100% 20%, 75% 35%, 50% 50%",
      delay: 0.3,
      duration: 2.8,
      color: "rgba(100, 220, 255, 0.5)",
    },
    {
      id: 11,
      path: "M 100% 40%, 75% 45%, 50% 50%",
      delay: 0.8,
      duration: 2.3,
      color: "rgba(100, 220, 255, 0.6)",
    },
    {
      id: 12,
      path: "M 100% 60%, 75% 55%, 50% 50%",
      delay: 1.3,
      duration: 2.3,
      color: "rgba(100, 220, 255, 0.6)",
    },
    {
      id: 13,
      path: "M 100% 80%, 75% 65%, 50% 50%",
      delay: 1.8,
      duration: 2.8,
      color: "rgba(100, 220, 255, 0.5)",
    },

    // Bottom cables
    {
      id: 14,
      path: "M 10% 100%, 30% 70%, 50% 50%",
      delay: 0.4,
      duration: 3,
      color: "rgba(100, 220, 255, 0.6)",
    },
    {
      id: 15,
      path: "M 30% 100%, 40% 75%, 50% 50%",
      delay: 0.9,
      duration: 2.5,
      color: "rgba(100, 220, 255, 0.5)",
    },
    {
      id: 16,
      path: "M 50% 100%, 50% 75%, 50% 50%",
      delay: 1.4,
      duration: 2,
      color: "rgba(100, 220, 255, 0.7)",
    },
    {
      id: 17,
      path: "M 70% 100%, 60% 75%, 50% 50%",
      delay: 1.9,
      duration: 2.5,
      color: "rgba(100, 220, 255, 0.5)",
    },
    {
      id: 18,
      path: "M 90% 100%, 70% 70%, 50% 50%",
      delay: 2.4,
      duration: 3,
      color: "rgba(100, 220, 255, 0.6)",
    },
  ], [])

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext("2d")
    if (!ctx) return

    // Set canvas dimensions
    const resizeCanvas = () => {
      canvas.width = window.innerWidth
      canvas.height = window.innerHeight
    }

    resizeCanvas()
    window.addEventListener("resize", resizeCanvas)

    // Function to parse SVG path and convert to canvas coordinates
    const parsePath = (pathStr: string, canvasWidth: number, canvasHeight: number) => {
      const points: [number, number][] = []
      const commands = pathStr.split(",")

      commands.forEach((cmd) => {
        const parts = cmd.trim().split(" ")
        if (parts.length === 2) {
          const x = (Number.parseFloat(parts[0]) / 100) * canvasWidth
          const y = (Number.parseFloat(parts[1]) / 100) * canvasHeight
          points.push([x, y])
        }
      })

      return points
    }

    // Animation loop
    let animationFrameId: number
    let lastTime = 0
    const fps = 60
    const interval = 1000 / fps

    const particles: {
      x: number
      y: number
      size: number
      speed: number
      cableId: number
      progress: number
      opacity: number
    }[] = []

    // Create initial particles for each cable
    cables.forEach((cable) => {
      const numParticles = 5 + Math.floor(Math.random() * 5) // 5-10 particles per cable
      for (let i = 0; i < numParticles; i++) {
        particles.push({
          x: 0,
          y: 0,
          size: 1 + Math.random() * 2,
          speed: 0.001 + Math.random() * 0.002,
          cableId: cable.id,
          progress: Math.random(), // Random starting position
          opacity: 0.3 + Math.random() * 0.7,
        })
      }
    })

    const animate = (timestamp: number) => {
      const deltaTime = timestamp - lastTime

      if (deltaTime >= interval) {
        lastTime = timestamp - (deltaTime % interval)

        // Clear canvas
        ctx.clearRect(0, 0, canvas.width, canvas.height)

        // Draw cables
        cables.forEach((cable) => {
          const points = parsePath(cable.path, canvas.width, canvas.height)
          if (points.length < 2) return

          // Draw cable path
          ctx.beginPath()
          ctx.moveTo(points[0][0], points[0][1])

          for (let i = 1; i < points.length; i++) {
            ctx.lineTo(points[i][0], points[i][1])
          }

          ctx.strokeStyle = cable.color.replace("0.6", "0.15") // Dimmer base cable
          ctx.lineWidth = 2
          ctx.stroke()
        })

        // Update and draw particles
        particles.forEach((particle) => {
          // Update particle position
          particle.progress += particle.speed
          if (particle.progress > 1) {
            particle.progress = 0
          }

          // Find the cable this particle belongs to
          const cable = cables.find((c) => c.id === particle.cableId)
          if (!cable) return

          const points = parsePath(cable.path, canvas.width, canvas.height)
          if (points.length < 2) return

          // Calculate position along the path based on progress
          const segmentIndex = Math.floor(particle.progress * (points.length - 1))
          const segmentProgress = (particle.progress * (points.length - 1)) % 1

          const startPoint = points[segmentIndex]
          const endPoint = points[Math.min(segmentIndex + 1, points.length - 1)]

          particle.x = startPoint[0] + (endPoint[0] - startPoint[0]) * segmentProgress
          particle.y = startPoint[1] + (endPoint[1] - startPoint[1]) * segmentProgress

          // Draw particle
          ctx.beginPath()
          ctx.arc(particle.x, particle.y, particle.size, 0, Math.PI * 2)
          ctx.fillStyle = cable.color.replace("0.6", particle.opacity.toString())
          ctx.fill()

          // Draw glow
          ctx.beginPath()
          ctx.arc(particle.x, particle.y, particle.size * 2, 0, Math.PI * 2)
          const gradient = ctx.createRadialGradient(
            particle.x,
            particle.y,
            particle.size,
            particle.x,
            particle.y,
            particle.size * 2,
          )
          gradient.addColorStop(0, cable.color.replace("0.6", (particle.opacity * 0.5).toString()))
          gradient.addColorStop(1, cable.color.replace("0.6", "0"))
          ctx.fillStyle = gradient
          ctx.fill()
        })
      }

      animationFrameId = requestAnimationFrame(animate)
    }

    animationFrameId = requestAnimationFrame(animate)

    return () => {
      window.removeEventListener("resize", resizeCanvas)
      cancelAnimationFrame(animationFrameId)
    }
  }, [cables])

  return <canvas ref={canvasRef} className="absolute inset-0 z-0 pointer-events-none" style={{ opacity: 0.8 }} />
}
