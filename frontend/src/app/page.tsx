"use client"

import type React from "react"

import { useState, useRef, useEffect } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { MessageSquare, ArrowRight, BarChart4, Database, BrainCircuit } from "lucide-react"
import { MotherboardBackground } from "@/components/motherboard-background"
import { useRouter } from "next/navigation"

export default function Home() {
  const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 })
  const [loadingChat, setLoadingChat] = useState(false)
  const [isTransitioning, setIsTransitioning] = useState(false)
  const [scrollY, setScrollY] = useState(0)
  const heroRef = useRef<HTMLDivElement>(null)
  const [flickerState, setFlickerState] = useState(1)
  const router = useRouter()

  // Track mouse position for spotlight effect
  const handleMouseMove = (e: React.MouseEvent) => {
    setMousePosition({
      x: e.clientX,
      y: e.clientY,
    })
  }

  // Track scroll position
  useEffect(() => {
    const handleScroll = () => {
      setScrollY(window.scrollY)
    }

    window.addEventListener("scroll", handleScroll)
    return () => window.removeEventListener("scroll", handleScroll)
  }, [])

  // Subtle text flicker effect
  useEffect(() => {
    const flickerInterval = setInterval(() => {
      // Random flicker effect - mostly at full opacity, occasionally flickers
      const newFlickerState = Math.random() > 0.92 ? Math.random() * 0.4 + 0.6 : 1
      setFlickerState(newFlickerState)
    }, 100)

    return () => clearInterval(flickerInterval)
  }, [])

  const handleStartChat = () => {
    setLoadingChat(true)
    setTimeout(() => {
      setIsTransitioning(true)
      setTimeout(() => {
        router.push("/chat")
        setIsTransitioning(false)
        setLoadingChat(false)
      }, 1000)
    }, 1500)
  }

  // Calculate spotlight opacity based on scroll position
  const spotlightOpacity = Math.max(0, 1 - scrollY / 300)

  // Calculate content opacity based on scroll position
  const contentOpacity = Math.min(1, (scrollY - 100) / 300)

  // Spotlight size - larger for better visibility
  const spotlightSize = 250

  return (
    <div className="min-h-screen bg-black text-white overflow-x-hidden">
      {/* Hero section with spotlight effect */}
      <div ref={heroRef} className="relative w-full h-screen overflow-hidden" onMouseMove={handleMouseMove}>
        {/* Motherboard background with animated cables */}
        <MotherboardBackground />

        {/* CPU core with AInalyst text - on same layer as motherboard */}
        <div className="absolute inset-0 z-10 flex items-center justify-center pointer-events-none">
          <div className="relative">
            <motion.div
              animate={{
                boxShadow: [
                  "0 0 30px rgba(100,220,255,0.3)",
                  "0 0 40px rgba(100,220,255,0.5)",
                  "0 0 30px rgba(100,220,255,0.3)",
                ],
              }}
              transition={{
                duration: 3,
                repeat: Infinity,
                repeatType: "reverse",
              }}
              style={{
                backdropFilter: "blur(6px)",
                backgroundColor: "rgba(0, 0, 0, 0.3)",
                border: "1px solid rgba(6, 182, 212, 0.5)",
                borderRadius: "6px",
                padding: "2rem",
                boxShadow: "0 0 30px rgba(100, 220, 255, 0.3)",
                overflow: "hidden",
              }}
            >
              {/* CPU grid lines */}
              <div className="absolute inset-0 grid grid-cols-8 grid-rows-8 opacity-30">
                {Array.from({ length: 8 }).map((_, i) => (
                  <div
                    key={`h-${i}`}
                    className="w-full h-px bg-cyan-400 transform translate-y-[calc(100%*var(--tw-translate-y))]"
                    style={{ "--tw-translate-y": i / 8 } as React.CSSProperties}
                  />
                ))}
                {Array.from({ length: 8 }).map((_, i) => (
                  <div
                    key={`v-${i}`}
                    className="h-full w-px bg-cyan-400 transform translate-x-[calc(100%*var(--tw-translate-x))]"
                    style={{ "--tw-translate-x": i / 8 } as React.CSSProperties}
                  />
                ))}
              </div>

              {/* Animated glow inside the box */}
              <div className="absolute inset-0 opacity-30">
                <div className="absolute inset-0 bg-gradient-to-r from-cyan-500/0 via-cyan-500/30 to-cyan-500/0 -translate-x-[100%] animate-glow-slow"></div>
              </div>

              {/* Scanlines overlay */}
              <div className="absolute inset-0 pointer-events-none overflow-hidden opacity-10">
                <div className="scanlines"></div>
              </div>

              {/* CPU pins/connectors - more visible now */}
              <div className="absolute -bottom-2 left-1/2 transform -translate-x-1/2 w-3/4 h-2 flex justify-around">
                {Array.from({ length: 12 }).map((_, i) => (
                  <div key={`pin-${i}`} className="w-1 h-full bg-cyan-400/70 rounded-b-sm"></div>
                ))}
              </div>

              <div className="absolute -top-2 left-1/2 transform -translate-x-1/2 w-3/4 h-2 flex justify-around">
                {Array.from({ length: 12 }).map((_, i) => (
                  <div key={`pin-top-${i}`} className="w-1 h-full bg-cyan-400/70 rounded-t-sm"></div>
                ))}
              </div>

              <div className="absolute -left-2 top-1/2 transform -translate-y-1/2 h-3/4 w-2 flex flex-col justify-around">
                {Array.from({ length: 8 }).map((_, i) => (
                  <div key={`pin-left-${i}`} className="h-1 w-full bg-cyan-400/70 rounded-l-sm"></div>
                ))}
              </div>

              <div className="absolute -right-2 top-1/2 transform -translate-y-1/2 h-3/4 w-2 flex flex-col justify-around">
                {Array.from({ length: 8 }).map((_, i) => (
                  <div key={`pin-right-${i}`} className="h-1 w-full bg-cyan-400/70 rounded-r-sm"></div>
                ))}
              </div>

              <h1
                className="text-[15vmin] font-orbitron font-bold tracking-wider select-none"
                style={{
                  color: "transparent",
                  WebkitTextStroke: `1px rgba(100, 220, 255, ${flickerState * 0.9})`,
                  filter: `drop-shadow(0 0 10px rgba(100, 220, 255, ${flickerState * 0.8}))`,
                  textShadow: `0 0 20px rgba(100, 220, 255, ${flickerState * 0.6}), 0 0 40px rgba(100, 220, 255, ${flickerState * 0.4})`,
                  opacity: flickerState,
                }}
              >
                AInalyst
              </h1>
            </motion.div>
          </div>
        </div>

        {/* Spotlight mask layer - unified for all elements */}
        <div
          className="absolute inset-0 z-20 pointer-events-none"
          style={{
            opacity: spotlightOpacity,
          }}
        >
          {/* This div provides the actual mask */}
          <div
            className="absolute inset-0 bg-black"
            style={{
              maskImage: `radial-gradient(circle ${spotlightSize}px at ${mousePosition.x}px ${mousePosition.y}px, transparent, black)`,
              WebkitMaskImage: `radial-gradient(circle ${spotlightSize}px at ${mousePosition.x}px ${mousePosition.y}px, transparent, black)`,
            }}
          ></div>
        </div>

        {/* Glassmorphism CTA button */}
        <div className="absolute bottom-20 w-full flex justify-center z-30" style={{ opacity: spotlightOpacity }}>
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.8, duration: 0.7 }}
          >
            <button
              onClick={handleStartChat}
              disabled={loadingChat}
              style={{
                position: "relative",
                overflow: "hidden",
                backdropFilter: "blur(6px)",
                backgroundColor: "rgba(0, 0, 0, 0.3)",
                border: "1px solid rgba(6, 182, 212, 0.5)",
                color: "white",
                padding: "1rem 2rem",
                borderRadius: "6px",
                fontWeight: "500",
                transition: "all 300ms",
                outline: "none",
              }}
            >
            {/* Button glow effect */}
            <span className="absolute inset-0 w-full h-full bg-gradient-to-r from-cyan-500/0 via-cyan-500/40 to-cyan-500/0 -translate-x-[100%] group-hover:animate-glow"></span>

            <span className="relative flex items-center gap-2">
              {loadingChat ? (
                <>
                  <div className="flex space-x-1 items-center">
                    <div
                      className="h-2 w-2 bg-white rounded-full animate-bounce"
                      style={{ animationDelay: "0ms" }}
                    ></div>
                    <div
                      className="h-2 w-2 bg-white rounded-full animate-bounce"
                      style={{ animationDelay: "150ms" }}
                    ></div>
                    <div
                      className="h-2 w-2 bg-white rounded-full animate-bounce"
                      style={{ animationDelay: "300ms" }}
                    ></div>
                  </div>
                  <span className="ml-2">Loading AInalyst...</span>
                </>
              ) : (
                <>
                  <MessageSquare className="h-5 w-5" />
                  <span>Enter AInalyst</span>
                  <ArrowRight className="h-5 w-5 ml-1" />
                </>
              )}
            </span>
            </button>
          </motion.div>
        </div>

        {/* Scroll indicator */}
        <div
          className="absolute bottom-8 left-1/2 transform -translate-x-1/2 flex flex-col items-center text-white/50 animate-pulse z-30"
          style={{ opacity: spotlightOpacity }}
        >
          <span className="text-xs mb-2">Scroll to learn more</span>
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path
              d="M12 5L12 19M12 19L19 12M12 19L5 12"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </div>
      </div>

      {/* Content section below spotlight */}
      <div
        className="relative z-30 min-h-screen bg-gradient-to-b from-gray-900 to-black py-20 px-6"
        style={{ opacity: contentOpacity }}
      >
        <div className="max-w-6xl mx-auto">
          {/* Tagline and description */}
          <div className="text-center mb-20">
            <h2 className="text-4xl md:text-5xl font-bold mb-6 text-white">
              Your AI-powered gateway to financial intelligence
            </h2>
            <p className="text-lg md:text-xl text-gray-300 max-w-3xl mx-auto">
              AInalyst uses Retrieval-Augmented Generation (RAG), powered by OpenAI models, to answer your financial
              questions using real-time data from the SEC API. Ask about a company&apos;s performance, strategy, management,
              or any other finance-related topic that comes to mind.
            </p>
          </div>

          {/* Feature cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-16">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
              viewport={{ once: true, margin: "-100px" }}
              style={{
                backgroundColor: "rgba(31, 41, 55, 0.5)",
                backdropFilter: "blur(4px)",
                border: "1px solid rgb(55, 65, 81)",
                borderRadius: "8px",
                padding: "2rem",
              }}
            >
              <div className="bg-cyan-900/50 p-3 rounded-lg w-12 h-12 flex items-center justify-center mb-6">
                <BarChart4 className="h-6 w-6 text-cyan-400" />
              </div>
              <h3 className="text-xl font-semibold mb-3 text-white">Real-Time Insights</h3>
              <p className="text-gray-300">Stay current with live financial data and trends.</p>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.1 }}
              viewport={{ once: true, margin: "-100px" }}
              style={{
                backgroundColor: "rgba(31, 41, 55, 0.5)",
                backdropFilter: "blur(4px)",
                border: "1px solid rgb(55, 65, 81)",
                borderRadius: "8px",
                padding: "2rem",
              }}
            >
              <div className="bg-cyan-900/50 p-3 rounded-lg w-12 h-12 flex items-center justify-center mb-6">
                <Database className="h-6 w-6 text-cyan-400" />
              </div>
              <h3 className="text-xl font-semibold mb-3 text-white">SEC-Backed Data</h3>
              <p className="text-gray-300">Pulled directly from official filings and disclosures.</p>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.2 }}
              viewport={{ once: true, margin: "-100px" }}
              style={{
                backgroundColor: "rgba(31, 41, 55, 0.5)",
                backdropFilter: "blur(4px)",
                border: "1px solid rgb(55, 65, 81)",
                borderRadius: "8px",
                padding: "2rem",
              }}
            >
              <div className="bg-cyan-900/50 p-3 rounded-lg w-12 h-12 flex items-center justify-center mb-6">
                <BrainCircuit className="h-6 w-6 text-cyan-400" />
              </div>
              <h3 className="text-xl font-semibold mb-3 text-white">RAG + OpenAI</h3>
              <p className="text-gray-300">
                Trusted answers powered by Retrieval-Augmented Generation and advanced language models.
              </p>
            </motion.div>
          </div>

          {/* CTA section */}
          <div className="text-center">
            <button
              onClick={handleStartChat}
              disabled={loadingChat}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "0.5rem",
                backgroundColor: "rgb(8, 145, 178)",
                color: "white",
                padding: "1rem 2rem",
                borderRadius: "6px",
                fontWeight: "500",
                transition: "background-color 300ms",
                opacity: loadingChat ? 0.8 : 1,
                border: "none",
                cursor: "pointer",
              }}
            >
              <MessageSquare className="h-5 w-5" />
              <span>{loadingChat ? "Loading..." : "Start Using AInalyst"}</span>
              <ArrowRight className="h-5 w-5 ml-1" />
            </button>
          </div>
        </div>
      </div>

      {/* Transition overlay */}
      <AnimatePresence>
        {isTransitioning && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.5 }}
            style={{
              position: "fixed",
              inset: 0,
              backgroundColor: "black",
              zIndex: 50,
            }}
          />
        )}
      </AnimatePresence>
    </div>
  )
}
