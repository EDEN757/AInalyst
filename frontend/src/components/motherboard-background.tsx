"use client"

import { useEffect, useRef } from "react"

interface CircuitPath {
  points: { x: number; y: number }[]
  pulses: {
    position: number
    speed: number
    size: number
    opacity: number
    tailLength: number
    hue: number
  }[]
  width: number
  color: string
}

// Easing functions for smoother animations
const easing = {
  easeInOut: (t: number): number => {
    return t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t
  },
  easeOut: (t: number): number => {
    return 1 - Math.pow(1 - t, 2)
  },
  easeIn: (t: number): number => {
    return t * t
  },
}

export function MotherboardBackground() {
  const canvasRef = useRef<HTMLCanvasElement>(null)

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

    // Define CPU dimensions and position (center of screen)
    const cpuWidth = Math.min(canvas.width * 0.3, 400)
    const cpuHeight = Math.min(canvas.height * 0.25, 200)
    const cpuX = canvas.width / 2 - cpuWidth / 2
    const cpuY = canvas.height / 2 - cpuHeight / 2

    // Create circuit paths with 90-degree angles
    const paths: CircuitPath[] = []

    // Function to create a path with 90-degree turns
    const createPath = (
      startX: number,
      startY: number,
      endX: number,
      endY: number,
      intermediatePoints = 1,
    ): { x: number; y: number }[] => {
      const points: { x: number; y: number }[] = [{ x: startX, y: startY }]

      if (intermediatePoints === 1) {
        // Simple L-shaped path
        const midPoint = { x: startX, y: endY }
        points.push(midPoint)
      } else if (intermediatePoints === 2) {
        // Z-shaped path
        const midX = startX + (endX - startX) / 2
        points.push({ x: midX, y: startY })
        points.push({ x: midX, y: endY })
      } else if (intermediatePoints === 3) {
        // More complex path with 3 turns
        const segment1 = (endX - startX) / 3
        const segment2 = (endY - startY) / 3

        points.push({ x: startX + segment1, y: startY })
        points.push({ x: startX + segment1, y: startY + segment2 * 2 })
        points.push({ x: endX - segment1, y: startY + segment2 * 2 })
        points.push({ x: endX - segment1, y: endY })
      }

      points.push({ x: endX, y: endY })
      return points
    }

    // Create paths from different edges of the screen to CPU connection points

    // Top edge paths
    for (let i = 0; i < 4; i++) {
      const startX = (canvas.width / 5) * (i + 1)
      const startY = 0

      // Calculate a connection point on the top edge of the CPU
      const connectionX = cpuX + (cpuWidth / 5) * (i + 1)
      const connectionY = cpuY

      const pathPoints = createPath(startX, startY, connectionX, connectionY, (i % 3) + 1)

      // Create multiple pulses with varied properties
      const numPulses = 3 + Math.floor(Math.random() * 3) // 3-5 pulses per path
      const pulses = Array(numPulses)
        .fill(0)
        .map(() => ({
          position: Math.random(),
          speed: 0.001 + Math.random() * 0.002,
          size: 1.5 + Math.random() * 1.5,
          opacity: 0.6 + Math.random() * 0.4,
          tailLength: 0.05 + Math.random() * 0.1, // Length of the trailing effect
          hue: 190 + Math.random() * 20, // Slight color variation in the cyan range
        }))

      paths.push({
        points: pathPoints,
        pulses,
        width: 2,
        color: "rgba(56, 189, 248, 0.8)",
      })
    }

    // Bottom edge paths
    for (let i = 0; i < 4; i++) {
      const startX = (canvas.width / 5) * (i + 1)
      const startY = canvas.height

      // Calculate a connection point on the bottom edge of the CPU
      const connectionX = cpuX + (cpuWidth / 5) * (i + 1)
      const connectionY = cpuY + cpuHeight

      const pathPoints = createPath(startX, startY, connectionX, connectionY, (i % 3) + 1)

      // Create multiple pulses with varied properties
      const numPulses = 3 + Math.floor(Math.random() * 3) // 3-5 pulses per path
      const pulses = Array(numPulses)
        .fill(0)
        .map(() => ({
          position: Math.random(),
          speed: 0.001 + Math.random() * 0.002,
          size: 1.5 + Math.random() * 1.5,
          opacity: 0.6 + Math.random() * 0.4,
          tailLength: 0.05 + Math.random() * 0.1,
          hue: 190 + Math.random() * 20,
        }))

      paths.push({
        points: pathPoints,
        pulses,
        width: 2,
        color: "rgba(56, 189, 248, 0.8)",
      })
    }

    // Left edge paths
    for (let i = 0; i < 3; i++) {
      const startX = 0
      const startY = (canvas.height / 4) * (i + 1)

      // Calculate a connection point on the left edge of the CPU
      const connectionX = cpuX
      const connectionY = cpuY + (cpuHeight / 4) * (i + 1)

      const pathPoints = createPath(startX, startY, connectionX, connectionY, (i % 3) + 1)

      // Create multiple pulses with varied properties
      const numPulses = 3 + Math.floor(Math.random() * 3) // 3-5 pulses per path
      const pulses = Array(numPulses)
        .fill(0)
        .map(() => ({
          position: Math.random(),
          speed: 0.001 + Math.random() * 0.002,
          size: 1.5 + Math.random() * 1.5,
          opacity: 0.6 + Math.random() * 0.4,
          tailLength: 0.05 + Math.random() * 0.1,
          hue: 190 + Math.random() * 20,
        }))

      paths.push({
        points: pathPoints,
        pulses,
        width: 2,
        color: "rgba(56, 189, 248, 0.8)",
      })
    }

    // Right edge paths
    for (let i = 0; i < 3; i++) {
      const startX = canvas.width
      const startY = (canvas.height / 4) * (i + 1)

      // Calculate a connection point on the right edge of the CPU
      const connectionX = cpuX + cpuWidth
      const connectionY = cpuY + (cpuHeight / 4) * (i + 1)

      const pathPoints = createPath(startX, startY, connectionX, connectionY, (i % 3) + 1)

      // Create multiple pulses with varied properties
      const numPulses = 3 + Math.floor(Math.random() * 3) // 3-5 pulses per path
      const pulses = Array(numPulses)
        .fill(0)
        .map(() => ({
          position: Math.random(),
          speed: 0.001 + Math.random() * 0.002,
          size: 1.5 + Math.random() * 1.5,
          opacity: 0.6 + Math.random() * 0.4,
          tailLength: 0.05 + Math.random() * 0.1,
          hue: 190 + Math.random() * 20,
        }))

      paths.push({
        points: pathPoints,
        pulses,
        width: 2,
        color: "rgba(56, 189, 248, 0.8)",
      })
    }

    // Add some additional cross-connections for complexity
    for (let i = 0; i < 4; i++) {
      const startX = i < 2 ? 0 : canvas.width
      const startY = i % 2 === 0 ? canvas.height / 3 : (canvas.height * 2) / 3

      // Connect to a random point on the CPU
      const side = Math.floor(Math.random() * 4) // 0: top, 1: right, 2: bottom, 3: left
      let connectionX, connectionY

      switch (side) {
        case 0: // top
          connectionX = cpuX + Math.random() * cpuWidth
          connectionY = cpuY
          break
        case 1: // right
          connectionX = cpuX + cpuWidth
          connectionY = cpuY + Math.random() * cpuHeight
          break
        case 2: // bottom
          connectionX = cpuX + Math.random() * cpuWidth
          connectionY = cpuY + cpuHeight
          break
        case 3: // left
          connectionX = cpuX
          connectionY = cpuY + Math.random() * cpuHeight
          break
        default:
          connectionX = cpuX + cpuWidth / 2
          connectionY = cpuY + cpuHeight / 2
      }

      const pathPoints = createPath(startX, startY, connectionX, connectionY, 2)

      // Create multiple pulses with varied properties
      const numPulses = 2 + Math.floor(Math.random() * 3) // 2-4 pulses per path
      const pulses = Array(numPulses)
        .fill(0)
        .map(() => ({
          position: Math.random(),
          speed: 0.0008 + Math.random() * 0.0015,
          size: 1.5 + Math.random() * 1.5,
          opacity: 0.6 + Math.random() * 0.4,
          tailLength: 0.05 + Math.random() * 0.1,
          hue: 190 + Math.random() * 20,
        }))

      paths.push({
        points: pathPoints,
        pulses,
        width: 1.5,
        color: "rgba(56, 189, 248, 0.7)",
      })
    }

    // Animation loop
    let animationFrameId: number
    let lastTime = 0
    const fps = 60
    const interval = 1000 / fps

    // Create PCB grid pattern
    const drawPCBGrid = () => {
      // Draw a subtle grid pattern
      ctx.strokeStyle = "rgba(56, 189, 248, 0.05)"
      ctx.lineWidth = 0.5

      // Horizontal grid lines
      for (let y = 0; y < canvas.height; y += 20) {
        ctx.beginPath()
        ctx.moveTo(0, y)
        ctx.lineTo(canvas.width, y)
        ctx.stroke()
      }

      // Vertical grid lines
      for (let x = 0; x < canvas.width; x += 20) {
        ctx.beginPath()
        ctx.moveTo(x, 0)
        ctx.lineTo(x, canvas.height)
        ctx.stroke()
      }
    }

    // Draw CPU connection points
    const drawCPUConnections = () => {
      // Top edge connection points
      for (let i = 1; i < 5; i++) {
        const x = cpuX + (cpuWidth / 5) * i
        const y = cpuY

        ctx.beginPath()
        ctx.rect(x - 2, y - 4, 4, 4)
        ctx.fillStyle = "rgba(56, 189, 248, 0.8)"
        ctx.fill()
      }

      // Bottom edge connection points
      for (let i = 1; i < 5; i++) {
        const x = cpuX + (cpuWidth / 5) * i
        const y = cpuY + cpuHeight

        ctx.beginPath()
        ctx.rect(x - 2, y, 4, 4)
        ctx.fillStyle = "rgba(56, 189, 248, 0.8)"
        ctx.fill()
      }

      // Left edge connection points
      for (let i = 1; i < 4; i++) {
        const x = cpuX
        const y = cpuY + (cpuHeight / 4) * i

        ctx.beginPath()
        ctx.rect(x - 4, y - 2, 4, 4)
        ctx.fillStyle = "rgba(56, 189, 248, 0.8)"
        ctx.fill()
      }

      // Right edge connection points
      for (let i = 1; i < 4; i++) {
        const x = cpuX + cpuWidth
        const y = cpuY + (cpuHeight / 4) * i

        ctx.beginPath()
        ctx.rect(x, y - 2, 4, 4)
        ctx.fillStyle = "rgba(56, 189, 248, 0.8)"
        ctx.fill()
      }
    }

    // Calculate position along path with easing
    const getPositionAlongPath = (
      path: { x: number; y: number }[],
      progress: number,
      easingFn: (t: number) => number,
    ) => {
      // Apply easing to the progress
      const easedProgress = easingFn(progress)

      // Calculate total path length
      let totalLength = 0
      for (let i = 0; i < path.length - 1; i++) {
        const dx = path[i + 1].x - path[i].x
        const dy = path[i + 1].y - path[i].y
        totalLength += Math.sqrt(dx * dx + dy * dy)
      }

      // Find position along the path
      const targetLength = easedProgress * totalLength
      let currentLength = 0
      let segmentIndex = 0
      let segmentPos = 0

      for (let i = 0; i < path.length - 1; i++) {
        const dx = path[i + 1].x - path[i].x
        const dy = path[i + 1].y - path[i].y
        const segmentLength = Math.sqrt(dx * dx + dy * dy)

        if (currentLength + segmentLength >= targetLength) {
          segmentIndex = i
          segmentPos = segmentLength > 0 ? (targetLength - currentLength) / segmentLength : 0
          break
        }

        currentLength += segmentLength
      }

      // Ensure segmentIndex is valid
      segmentIndex = Math.min(segmentIndex, path.length - 2)

      // Calculate position
      const startPoint = path[segmentIndex]
      const endPoint = path[segmentIndex + 1]

      return {
        x: startPoint.x + (endPoint.x - startPoint.x) * segmentPos,
        y: startPoint.y + (endPoint.y - startPoint.y) * segmentPos,
      }
    }

    const animate = (timestamp: number) => {
      const deltaTime = timestamp - lastTime

      if (deltaTime >= interval) {
        lastTime = timestamp - (deltaTime % interval)

        // Clear canvas
        ctx.clearRect(0, 0, canvas.width, canvas.height)

        // Draw PCB grid background
        drawPCBGrid()

        // Draw circuit paths
        paths.forEach((path) => {
          // Draw path
          ctx.beginPath()
          ctx.moveTo(path.points[0].x, path.points[0].y)

          for (let i = 1; i < path.points.length; i++) {
            ctx.lineTo(path.points[i].x, path.points[i].y)
          }

          ctx.strokeStyle = path.color.replace(/[\d.]+\)$/, "0.2)")
          ctx.lineWidth = path.width
          ctx.stroke()

          // Update and draw pulses with trails
          path.pulses.forEach((pulse) => {
            // Update pulse position
            pulse.position += pulse.speed
            if (pulse.position > 1) {
              pulse.position = 0
            }

            // Draw trail effect (multiple fading points)
            const trailSteps = 10
            for (let i = 0; i < trailSteps; i++) {
              // Calculate trail position (behind the pulse)
              const trailPos = Math.max(0, pulse.position - pulse.tailLength * (i / trailSteps))

              // Skip if trail position is negative or zero
              if (trailPos <= 0) continue

              // Get position with easing
              const pos = getPositionAlongPath(path.points, trailPos, easing.easeOut)

              // Calculate fade based on position in trail
              const fadeFactor = 1 - i / trailSteps

              // Draw trail segment
              const trailSize = pulse.size * fadeFactor * 0.8
              const trailOpacity = pulse.opacity * fadeFactor * 0.7

              // Use HSL for better color control
              const hslColor = `hsla(${pulse.hue}, 100%, 70%, ${trailOpacity})`

              ctx.beginPath()
              ctx.arc(pos.x, pos.y, trailSize, 0, Math.PI * 2)
              ctx.fillStyle = hslColor
              ctx.fill()
            }

            // Get main pulse position with easing
            const pos = getPositionAlongPath(path.points, pulse.position, easing.easeInOut)

            // Draw main pulse
            ctx.beginPath()
            ctx.arc(pos.x, pos.y, pulse.size, 0, Math.PI * 2)
            ctx.fillStyle = `hsla(${pulse.hue}, 100%, 70%, ${pulse.opacity})`
            ctx.fill()

            // Draw glow effect
            const glowSize = pulse.size * 3
            ctx.beginPath()
            ctx.arc(pos.x, pos.y, glowSize, 0, Math.PI * 2)
            const gradient = ctx.createRadialGradient(pos.x, pos.y, pulse.size, pos.x, pos.y, glowSize)
            gradient.addColorStop(0, `hsla(${pulse.hue}, 100%, 70%, ${pulse.opacity * 0.5})`)
            gradient.addColorStop(1, `hsla(${pulse.hue}, 100%, 70%, 0)`)
            ctx.fillStyle = gradient
            ctx.fill()
          })
        })

        // Draw CPU connection points
        drawCPUConnections()
      }

      animationFrameId = requestAnimationFrame(animate)
    }

    animationFrameId = requestAnimationFrame(animate)

    return () => {
      window.removeEventListener("resize", resizeCanvas)
      cancelAnimationFrame(animationFrameId)
    }
  }, [])

  return <canvas ref={canvasRef} className="absolute inset-0 z-10 pointer-events-none" style={{ opacity: 1 }} />
}
