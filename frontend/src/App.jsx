import { useState, useEffect, useRef, useCallback } from 'react'
import './index.css'
import NeuralBackground from './components/NeuralBackground'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import {
  Sparkles,
  Terminal,
  Activity,
  FileText,
  Cpu,
  CheckCircle2,
  Download,
  Play,
  Compass,
  Database,
  ClipboardCheck,
  Clock,
  Info,
  PenLine,
  ArrowDown,
  Zap,
} from 'lucide-react'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const WS_URL  = import.meta.env.VITE_WS_URL  || 'ws://localhost:8000'

const AGENTS = [
  { key: 'planner',   label: 'PLAN'  },
  { key: 'retriever', label: 'RTRV'  },
  { key: 'analyzer',  label: 'ANLYZ' },
  { key: 'writer',    label: 'WRITE' },
  { key: 'validator', label: 'VALID' },
]

const EXAMPLE_QUERIES = [
  'AI Trends in Healthcare',
  'Climate Change Global Economy',
  'Quantum Computing 2024',
  'Renewable Energy Adoption',
]

function formatTime(date) {
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

function truncate(str, n = 60) {
  return str && str.length > n ? str.slice(0, n) + '...' : str
}

// ── Animated counter for stat numbers ─────────────────────────────────────────
function StatPill({ value, label }) {
  return (
    <div className="hero-stat">
      <span className="hero-stat-value">{value}</span>
      <span className="hero-stat-label">{label}</span>
    </div>
  )
}

// ── Hero Section ───────────────────────────────────────────────────────────────
function HeroSection({ consoleRef }) {
  const scrollToConsole = () => {
    consoleRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  return (
    <section className="hero">
      {/* Luxury Gold Ambient Glow */}
      <div className="hero-ambient-glow" />

      {/* Main content */}
      <div className="hero-body">
        <div className="hero-label">
          <span>ORCHESTRATION CONSOLE</span>
        </div>

        <h1 className="hero-title">
          <span className="hero-title-word hero-title-word--1">MAESTRO</span>
          <span className="hero-title-word hero-title-word--2">AI</span>
        </h1>

        <p className="hero-tagline">
          An elite multi-agent system coordinating five specialized intelligences — 
          Planner, Retriever, Analyzer, Writer, and Validator — working in absolute concert 
          to transform raw directives into verified, high-fidelity intelligence.
        </p>

        <div className="hero-stats">
          <StatPill value="5" label="Specialized Agents" />
          <div className="hero-stats-divider" />
          <StatPill value="70B" label="LLM Parameters" />
          <div className="hero-stats-divider" />
          <StatPill value="100%" label="Autonomous Flow" />
        </div>

        <div className="hero-actions">
          <button
            id="hero-launch-btn"
            className="hero-btn hero-btn--primary"
            onClick={scrollToConsole}
          >
            <Zap size={14} strokeWidth={2.5} />
            <span>LAUNCH CONSOLE</span>
          </button>
          <button
            className="hero-btn hero-btn--outline"
            onClick={scrollToConsole}
          >
            <span>VIEW PIPELINE</span>
            <ArrowDown size={14} strokeWidth={2} />
          </button>
        </div>
      </div>

      {/* Scroll hint */}
      <button className="hero-scroll-hint" onClick={scrollToConsole} aria-label="Scroll to console">
        <div className="hero-scroll-track">
          <div className="hero-scroll-thumb" />
        </div>
        <span>EXPLORE SYSTEM</span>
      </button>
    </section>
  )
}

// ── Loader Component ─────────────────────────────────────────────────────────────
function Loader({ onComplete }) {
  const [progress, setProgress] = useState(0)
  const [stageText, setStageText] = useState('BOOTING ORCHESTRATION NEXUS...')

  const BOOT_AGENTS = [
    { key: 'planner',   label: 'PLAN',  range: [1, 20],   cx: 160, cy: 65,  textX: 160, textY: 46,  align: 'middle' },
    { key: 'retriever', label: 'RTRV',  range: [20, 40],  cx: 250, cy: 131, textX: 265, textY: 135, align: 'start' },
    { key: 'analyzer',  label: 'ANLYZ', range: [40, 60],  cx: 216, cy: 237, textX: 232, textY: 256, align: 'start' },
    { key: 'writer',    label: 'WRITE', range: [60, 80],  cx: 104, cy: 237, textX: 88,  textY: 256, align: 'end' },
    { key: 'validator', label: 'VALID', range: [80, 100], cx: 70,  cy: 131, textX: 55,  textY: 135, align: 'end' },
  ]

  useEffect(() => {
    window.scrollTo(0, 0)
    
    const interval = setInterval(() => {
      setProgress(prev => {
        if (prev >= 100) {
          clearInterval(interval)
          setTimeout(onComplete, 800) // Showcase 100% calibration
          return 100
        }
        
        const next = prev + Math.floor(Math.random() * 8) + 4
        const clamped = Math.min(next, 100)
        
        if (clamped < 20) {
          setStageText('PLANNER ENGINE BOOTSTRAP...')
        } else if (clamped < 40) {
          setStageText('RETRIEVER VECTOR SYNC...')
        } else if (clamped < 60) {
          setStageText('ANALYZER WEIGHTS ALIGNMENT...')
        } else if (clamped < 80) {
          setStageText('WRITER BUFFERS PREPARATION...')
        } else if (clamped < 100) {
          setStageText('VALIDATOR ENGINE FEEDBACK...')
        } else {
          setStageText('SYSTEM NEXUS SYNCHRONIZED.')
        }

        return clamped
      })
    }, 100)

    return () => clearInterval(interval)
  }, [onComplete])

  return (
    <div className="loader-screen">
      <div className="loader-ambient-glow" />

      
      <div className="loader-content">
        <div className="loader-brand">
          <div className="loader-logo-symbol">M</div>
          <h1 className="loader-title">MAESTRO AI</h1>
          <p className="loader-subtitle">ORCHESTRATION NEXUS</p>
        </div>

        {/* 5-Directional Constellation Map */}
        <div className="loader-constellation">
          <svg className="constellation-svg" viewBox="0 0 320 320" width="300" height="300">
            <defs>
              <filter id="loader-glow" x="-20%" y="-20%" width="140%" height="140%">
                <feGaussianBlur stdDeviation="5" result="blur" />
                <feMerge>
                  <feMergeNode in="blur" />
                  <feMergeNode in="SourceGraphic" />
                </feMerge>
              </filter>
            </defs>

            {/* Background geometric grid */}
            <polygon
              points="160,65 250,131 216,237 104,237 70,131"
              className="constellation-grid-loop"
            />

            {/* Connector lines from core to outer nodes */}
            {BOOT_AGENTS.map((agent) => {
              const isReady = progress >= agent.range[1]
              const isBooting = progress >= agent.range[0] && progress < agent.range[1]
              const statusClass = isReady ? 'ready' : isBooting ? 'booting' : 'pending'

              return (
                <line
                  key={`line-${agent.key}`}
                  x1="160"
                  y1="160"
                  x2={agent.cx}
                  y2={agent.cy}
                  className={`constellation-vector vector--${statusClass}`}
                />
              )
            })}

            {/* Central Nexus Core */}
            <g className="constellation-core">
              <circle cx="160" cy="160" r="30" className="core-dash-ring" />
              <circle cx="160" cy="160" r="22" className="core-shield" />
              <circle cx="160" cy="160" r="14" className="core-nucleus" />
            </g>

            {/* Outer agent nodes and labels */}
            {BOOT_AGENTS.map((agent) => {
              const isReady = progress >= agent.range[1]
              const isBooting = progress >= agent.range[0] && progress < agent.range[1]
              const statusClass = isReady ? 'ready' : isBooting ? 'booting' : 'pending'

              return (
                <g key={`node-${agent.key}`} className={`constellation-node node--${statusClass}`}>
                  <circle cx={agent.cx} cy={agent.cy} r="10" className="node-outer-glow" />
                  <circle cx={agent.cx} cy={agent.cy} r="6" className="node-mid-ring" />
                  <circle cx={agent.cx} cy={agent.cy} r="3" className="node-center-dot" />
                  <text
                    x={agent.textX}
                    y={agent.textY}
                    textAnchor={agent.align}
                    className="node-text"
                  >
                    {agent.label}
                  </text>
                </g>
              )
            })}
          </svg>
        </div>

        {/* Minimal Progress Bar & Percentage */}
        <div className="loader-status-block">
          <span className="loader-percentage">{progress}%</span>
          <div className="loader-bar">
            <div className="loader-bar-fill" style={{ width: `${progress}%` }} />
          </div>
          <span className="loader-stage-text">{stageText}</span>
        </div>
      </div>
    </div>
  )
}

// ── Header ─────────────────────────────────────────────────────────────────────
function Header({ taskId, status, secondsElapsed }) {
  const formatElapsed = (sec) => {
    const m = Math.floor(sec / 60).toString().padStart(2, '0')
    const s = (sec % 60).toString().padStart(2, '0')
    return `${m}:${s}`
  }

  return (
    <header className="header">
      <div className="header-brand">
        <div className="header-logo">M</div>
        <div className="header-title-group">
          <span className="header-title">MAESTRO AI</span>
          <span className="header-sub">v3.0.0 &mdash; Orchestration Console</span>
        </div>
      </div>

      <div className="header-controls">
        {status === 'running' && (
          <div className="clock-badge">
            <Clock size={13} className="spin-slow" />
            <span>ELAPSED: {formatElapsed(secondsElapsed)}</span>
          </div>
        )}
        {taskId && (
          <div className="task-badge">
            <span>TASK</span>
            <strong>{taskId.slice(0, 8)}</strong>
            <span className={`status-pill ${status || 'idle'}`}>
              {(status || 'idle').toUpperCase()}
            </span>
          </div>
        )}
        <div className="sys-badge">
          <div className="sys-dot" />
          <span>ONLINE</span>
        </div>
      </div>
    </header>
  )
}

// ── Query Input ────────────────────────────────────────────────────────────────
function QueryInput({ onSubmit, loading }) {
  const [query, setQuery] = useState('')

  const handleSubmit = (e) => {
    e.preventDefault()
    e.stopPropagation()
    // Blur active element immediately to prevent browser scroll-chasing
    // when the submit button becomes disabled after click
    if (document.activeElement) document.activeElement.blur()
    if (query.trim() && !loading) onSubmit(query.trim())
  }

  return (
    <section className="card card--rise">
      <div className="card-header">
        <div className="card-title">
          <Play size={14} strokeWidth={2.5} />
          <span>Directive Input</span>
        </div>
        <span className="card-meta">LLM: Llama3-70b</span>
      </div>
      <div className="card-body">
        <form className="query-form" onSubmit={handleSubmit}>
          <textarea
            id="query-input"
            className="query-textarea"
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="Enter a research directive..."
            rows={4}
            disabled={loading}
          />
          <div className="query-actions">
            <div className="query-chips">
              {EXAMPLE_QUERIES.map((q, i) => (
                <button
                  key={i}
                  type="button"
                  className="chip"
                  onClick={() => setQuery(q)}
                  disabled={loading}
                >
                  {truncate(q, 36)}
                </button>
              ))}
            </div>
            <button
              id="submit-task-btn"
              type="submit"
              className="run-btn"
              disabled={loading || !query.trim()}
            >
              {loading ? (
                <>
                  <div className="spinner" />
                  <span>PROCESSING</span>
                </>
              ) : (
                <>
                  <Sparkles size={14} strokeWidth={2.5} />
                  <span>RUN</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </section>
  )
}

// ── Agent Pipeline ─────────────────────────────────────────────────────────────
function AgentPipeline({ agentStates }) {
  const isLineActive = (i) => {
    const keys = ['planner', 'retriever', 'analyzer', 'writer', 'validator']
    const from = agentStates[keys[i]]
    const to   = agentStates[keys[i + 1]]
    return from === 'completed' || to === 'running' || to === 'completed'
  }
  const isLineRunning = (i) => {
    const keys = ['planner', 'retriever', 'analyzer', 'writer', 'validator']
    return agentStates[keys[i + 1]] === 'running'
  }

  const getIcon = (key) => {
    switch (key) {
      case 'planner':   return <Compass size={17} strokeWidth={1.8} />
      case 'retriever': return <Database size={17} strokeWidth={1.8} />
      case 'analyzer':  return <Cpu size={17} strokeWidth={1.8} />
      case 'writer':    return <PenLine size={17} strokeWidth={1.8} />
      case 'validator': return <ClipboardCheck size={17} strokeWidth={1.8} />
      default:          return <Cpu size={17} strokeWidth={1.8} />
    }
  }

  return (
    <section className="card card--rise card--delay-1">
      <div className="card-header">
        <div className="card-title">
          <Activity size={14} strokeWidth={2.5} />
          <span>Pipeline Conduit</span>
        </div>
      </div>
      <div className="card-body">
        <div className="conduit-wrap">
          <div className="conduit-row">
            {/* SVG connectors */}
            <svg className="conduit-svg">
              {[0, 1, 2, 3].map(i => (
                <g key={i}>
                  <line
                    x1={`${10 + i * 20}%`} y1="50%"
                    x2={`${30 + i * 20}%`} y2="50%"
                    className="conn-bg"
                  />
                  {isLineActive(i) && (
                    <line
                      x1={`${10 + i * 20}%`} y1="50%"
                      x2={`${30 + i * 20}%`} y2="50%"
                      className={`conn-active ${isLineRunning(i) ? 'conn-pulse' : ''}`}
                    />
                  )}
                </g>
              ))}
            </svg>

            {AGENTS.map((agent) => {
              const state = agentStates[agent.key] || 'idle'
              return (
                <div key={agent.key} className={`node node--${state}`}>
                  <div className="node-ring" />
                  <div className="node-icon">
                    {state === 'completed'
                      ? <CheckCircle2 size={17} strokeWidth={2} />
                      : getIcon(agent.key)
                    }
                    {state === 'completed' && <div className="node-burst" />}
                  </div>
                  <span className="node-label">{agent.label}</span>
                </div>
              )
            })}
          </div>

          {/* Phase progress bar */}
          <div className="phase-track">
            {AGENTS.map((agent) => {
              const state = agentStates[agent.key] || 'idle'
              return <div key={agent.key} className={`phase-seg phase-seg--${state}`} />
            })}
          </div>
        </div>
      </div>
    </section>
  )
}

// ── Stream Log ─────────────────────────────────────────────────────────────────
function StreamLog({ entries }) {
  const bodyRef = useRef(null)

  // Scroll ONLY within the stream-body container — never the page
  useEffect(() => {
    if (entries.length > 0 && bodyRef.current) {
      bodyRef.current.scrollTop = bodyRef.current.scrollHeight
    }
  }, [entries])

  return (
    <section className="card stream-card card--rise">
      <div className="card-header">
        <div className="card-title">
          <Terminal size={14} strokeWidth={2.5} />
          <span>Live Log Stream</span>
        </div>
        <span className="card-meta">{entries.length} EVENTS</span>
      </div>
      <div className="stream-body" ref={bodyRef}>
        {entries.length === 0 ? (
          <div className="stream-empty">
            <Terminal size={20} strokeWidth={1.5} />
            <span>Awaiting directive...</span>
          </div>
        ) : (
          entries.map((entry, i) => (
            <div key={i} className={`log-line event-${entry.event}`}>
              <span className="log-ts">[{entry.time}]</span>
              <span className={`log-tag tag-${entry.agent}`}>{entry.agent}</span>
              <span className="log-text">{entry.content}</span>
            </div>
          ))
        )}
      </div>
    </section>
  )
}

// ── Final Report ───────────────────────────────────────────────────────────────
function FinalReport({ report, validation }) {
  const handleDownload = () => {
    const blob = new Blob([report], { type: 'text/markdown' })
    const url  = URL.createObjectURL(blob)
    const a    = document.createElement('a')
    a.href     = url
    a.download = 'maestro-report.md'
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <section className={`card report-card card--rise card--delay-1 ${report ? 'report-card--ready' : ''}`}>
      <div className="card-header">
        <div className="card-title">
          <FileText size={14} strokeWidth={2.5} />
          <span>Report Artifact</span>
        </div>
        {report && (
          <button className="dl-btn" onClick={handleDownload} id="download-report-btn">
            <Download size={13} />
            <span>Download .MD</span>
          </button>
        )}
      </div>
      <div className="report-body">
        {!report ? (
          <div className="report-empty">
            <FileText size={20} strokeWidth={1.5} />
            <span>No artifact generated yet.</span>
          </div>
        ) : (
          <div className="report-md">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{report}</ReactMarkdown>
          </div>
        )}
      </div>
      {validation && (
        <div className="val-bar">
          <span className="val-label">
            <Info size={12} />
            QUALITY SCORE
          </span>
          <div className="val-score">
            <div className="val-track">
              <div
                className="val-fill"
                style={{
                  width: `${validation.score || 0}%`,
                  background:
                    validation.score >= 80 ? '#36d9a0'
                    : validation.score >= 60 ? '#f5b940'
                    : '#f2566e',
                }}
              />
            </div>
            <span
              className="val-num"
              style={{
                color: validation.score >= 80 ? '#36d9a0' : validation.score >= 60 ? '#f5b940' : '#f2566e',
              }}
            >
              {validation.score}%
            </span>
          </div>
          <span className="val-summary">{validation.summary}</span>
          {validation.valid && (
            <span className="val-pass">
              <CheckCircle2 size={11} />
              PASS
            </span>
          )}
        </div>
      )}
    </section>
  )
}

// ── App Root ───────────────────────────────────────────────────────────────────
export default function App() {
  const [loading,        setLoading]        = useState(false)
  const [taskId,         setTaskId]         = useState(null)
  const [taskStatus,     setTaskStatus]     = useState('idle')
  const [logEntries,     setLogEntries]     = useState([])
  const [agentStates,    setAgentStates]    = useState({})
  const [finalReport,    setFinalReport]    = useState(null)
  const [validation,     setValidation]     = useState(null)
  const [secondsElapsed, setSecondsElapsed] = useState(0)

  const [showLoader,      setShowLoader]      = useState(true)
  const [triggerEntrance, setTriggerEntrance] = useState(false)

  const wsRef      = useRef(null)
  const consoleRef = useRef(null)   // <-- Hero buttons scroll to this

  // Disable native scroll restoration & force instant scrollTo(0,0) on mount
  useEffect(() => {
    if ('scrollRestoration' in window.history) {
      window.history.scrollRestoration = 'manual'
    }
    window.scrollTo(0, 0)
  }, [])

  // Strict scroll lock while loader is active
  useEffect(() => {
    if (showLoader) {
      document.body.classList.add('loader-active')
      window.scrollTo(0, 0)
      
      const lockScroll = () => {
        if (window.scrollY !== 0) {
          window.scrollTo(0, 0)
        }
      }
      window.addEventListener('scroll', lockScroll)
      return () => {
        window.removeEventListener('scroll', lockScroll)
      }
    } else {
      document.body.classList.remove('loader-active')
      
      // Multi-frame robust scroll reset to absolute zero to prevent vertical lift
      let frames = 0
      const reset = () => {
        window.scrollTo(0, 0)
        frames++
        if (frames < 10) {
          requestAnimationFrame(reset)
        }
      }
      requestAnimationFrame(reset)
    }
  }, [showLoader])

  useEffect(() => {
    let interval = null
    if (taskStatus === 'running') {
      interval = setInterval(() => setSecondsElapsed(p => p + 1), 1000)
    } else if (taskStatus === 'idle' || taskStatus === 'pending') {
      setSecondsElapsed(0)
    }
    return () => { if (interval) clearInterval(interval) }
  }, [taskStatus])

  const addLog = useCallback((event, agent, content) => {
    setLogEntries(prev => [...prev, { event, agent: agent || 'system', content, time: formatTime(new Date()) }])
  }, [])

  const updateAgentState = useCallback((agent, state) => {
    setAgentStates(prev => ({ ...prev, [agent]: state }))
  }, [])

  const handleMessage = useCallback((data) => {
    const { event, agent, content, report, validation: val } = data
    addLog(event, agent, content)
    if (event === 'started') {
      updateAgentState(agent, 'running')
      setTaskStatus('running')
    } else if (event === 'completed') {
      updateAgentState(agent, 'completed')
    } else if (event === 'failed') {
      updateAgentState(agent, 'failed')
    } else if (event === 'final') {
      if (report) setFinalReport(report)
      if (val)    setValidation(val)
      setTaskStatus('completed')
      setLoading(false)
      setAgentStates(prev => {
        const next = { ...prev }
        AGENTS.forEach(a => { if (next[a.key] !== 'failed') next[a.key] = 'completed' })
        return next
      })
    }
  }, [addLog, updateAgentState])

  const connectWebSocket = useCallback((id) => {
    if (wsRef.current) wsRef.current.close()
    const ws = new WebSocket(`${WS_URL}/stream/${id}`)
    wsRef.current = ws
    ws.onopen    = () => addLog('connected', 'system', `Connected to stream -- TASK:${id.slice(0, 8)}`)
    ws.onmessage = (e) => { try { handleMessage(JSON.parse(e.data)) } catch (err) { console.error(err) } }
    ws.onerror   = () => addLog('failed', 'system', 'Stream connection fault')
    ws.onclose   = () => addLog('connected', 'system', 'Stream channel closed')
  }, [addLog, handleMessage])

  const handleSubmit = async (query) => {
    setLoading(true)
    setLogEntries([])
    setAgentStates({})
    setFinalReport(null)
    setValidation(null)
    setTaskStatus('pending')
    setTaskId(null)
    setSecondsElapsed(0)
    try {
      const res = await fetch(`${API_URL}/submit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query }),
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Submission failed')
      }
      const { task_id } = await res.json()
      setTaskId(task_id)
      addLog('connected', 'system', `Directive submitted -- TASK:${task_id.slice(0, 8)}`)
      connectWebSocket(task_id)
    } catch (err) {
      addLog('failed', 'system', `Error: ${err.message}`)
      setLoading(false)
      setTaskStatus('failed')
    }
  }

  useEffect(() => () => wsRef.current?.close(), [])

  return (
    <div className={`app ${triggerEntrance ? 'app--entrance' : ''} ${showLoader ? 'app--loading' : ''}`}>
      {showLoader && (
        <Loader
          onComplete={() => {
            // Instantly reset scroll to 0,0 right at the start of transition!
            window.scrollTo({ top: 0, left: 0, behavior: 'instant' })
            setTriggerEntrance(true)

            // Multiple frames safety trigger for absolute scroll anchoring
            const resetTimer = setInterval(() => {
              window.scrollTo(0, 0)
            }, 50)

            setTimeout(() => {
              clearInterval(resetTimer)
              setShowLoader(false)
              window.scrollTo({ top: 0, left: 0, behavior: 'instant' })
            }, 800) // Duration of transition animations
          }}
        />
      )}
      {/* Global ambient */}
      <div className="nebula-bg">
        <div className="nebula nebula-1" />
        <div className="nebula nebula-2" />
        <div className="nebula nebula-3" />
      </div>
      <NeuralBackground
        color="#e5c158"
        trailOpacity={0.06}
        particleCount={250}
        speed={0.4}
      />

      {/*
        HERO — sits at top of normal page flow.
        Workspace is directly below it. Scroll works naturally.
      */}
      <HeroSection consoleRef={consoleRef} />

      {/* WORKSPACE — always mounted to prevent reflow/unmount race conditions, hidden via CSS while loading */}
      <div className={`workspace ${showLoader ? 'workspace--hidden' : ''}`} ref={consoleRef}>
        <Header taskId={taskId} status={taskStatus} secondsElapsed={secondsElapsed} />
        <main className="main">
          <div className="col-left">
            <QueryInput onSubmit={handleSubmit} loading={loading} />
            <AgentPipeline agentStates={agentStates} />
          </div>
          <div className="col-right">
            <StreamLog entries={logEntries} />
            <FinalReport report={finalReport} validation={validation} />
          </div>
        </main>
      </div>
    </div>
  )
}
