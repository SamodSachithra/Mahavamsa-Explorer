import { useState, useEffect, useRef } from "react"
import axios from "axios"
import { MapContainer, TileLayer, Marker, Popup } from "react-leaflet"
import "leaflet/dist/leaflet.css"
import L from "leaflet"

delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png",
  iconUrl:       "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png",
  shadowUrl:     "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png",
})

const API = "http://localhost:8000"

const SRI_LANKA_IMAGES = [
  { url: "/images/sigiriya.jpg",      caption: "Sigiriya Rock Fortress" },
  { url: "/images/anuradhapura.jpg",  caption: "Ruwanwelisaya Stupa, Anuradhapura" },
  { url: "/images/polonnaruwa.jpg",   caption: "Polonnaruwa Vatadage" },
]

const SUGGESTED = [
  { icon: "👑", text: "Who was Vijaya?" },
  { icon: "⚔️", text: "Who defeated Elara?" },
  { icon: "🏛️", text: "What did Dutugamunu build?" },
  { icon: "📍", text: "How to go to Polonnaruwa?" },
  { icon: "🗺️", text: "Where is Sigiriya?" },
  { icon: "🏯", text: "How to visit Anuradhapura?" },
]

export default function App() {
  const [question, setQuestion]               = useState("")
  const [answer, setAnswer]                   = useState("")
  const [loading, setLoading]                 = useState(false)
  const [mode, setMode]                       = useState("graph")
  const [sites, setSites]                     = useState([])
  const [stats, setStats]                     = useState(null)
  const [history, setHistory]                 = useState([])
  const [triples, setTriples]                 = useState([])
  const [activeTab, setActiveTab]             = useState("chat")
  const [imgIndex, setImgIndex]               = useState(0)
  const [visible, setVisible]                 = useState(false)
  const [highlightSite, setHighlightSite]     = useState(null)
  const [languages, setLanguages]             = useState([])
  const [translating, setTranslating]         = useState(false)
  const [translatedAnswer, setTranslatedAnswer] = useState("")
  const [selectedLang, setSelectedLang]       = useState(null)
  const [showLangPicker, setShowLangPicker]   = useState(false)
  const answerRef = useRef(null)

  useEffect(() => {
    axios.get(`${API}/sites`).then(r => setSites(r.data.sites)).catch(() => {})
    axios.get(`${API}/stats`).then(r => setStats(r.data)).catch(() => {})
    axios.get(`${API}/languages`).then(r => setLanguages(r.data.languages)).catch(() => {})
    setTimeout(() => setVisible(true), 100)
    const iv = setInterval(() => setImgIndex(i => (i + 1) % SRI_LANKA_IMAGES.length), 5000)
    return () => clearInterval(iv)
  }, [])

  useEffect(() => {
    if (answer && answerRef.current) {
      answerRef.current.scrollIntoView({ behavior: "smooth", block: "start" })
    }
  }, [answer])

  const switchMode = (newMode) => {
    setMode(newMode)
    setAnswer("")
    setTriples([])
    setTranslatedAnswer("")
    setSelectedLang(null)
    setShowLangPicker(false)
    setHighlightSite(null)
  }

  const translateAnswer = async (langCode, langName) => {
    if (!answer) return
    setTranslating(true)
    setSelectedLang(langName)
    setTranslatedAnswer("")
    setShowLangPicker(false)
    try {
      const res = await axios.post(`${API}/translate`, {
        text:        answer,
        target_lang: langCode,
      })
      setTranslatedAnswer(res.data.translated)
    } catch {
      setTranslatedAnswer("Translation failed. Please try again.")
    }
    setTranslating(false)
  }

  const askQuestion = async (q) => {
    const query = q || question
    if (!query.trim()) return
    setQuestion(query)
    setLoading(true)
    setAnswer("")
    setTriples([])
    setHighlightSite(null)
    setTranslatedAnswer("")
    setSelectedLang(null)
    setShowLangPicker(false)

    try {
      const res = mode === "dual_agent"
        ? await axios.post(`${API}/ask_agents`, { question: query })
        : await axios.post(`${API}/ask`, { question: query, mode })

      const answerText = mode === "dual_agent" ? res.data.final_answer : res.data.answer
      setAnswer(answerText)
      setTriples(res.data.graph_triples || [])
      setHistory(prev => [
        { question: query, answer: answerText, mode },
        ...prev.slice(0, 9),
      ])
      if (res.data.location_site) {
        setHighlightSite(res.data.location_site)
      }
    } catch {
      setAnswer("Could not reach the backend. Please ensure the API server is running on port 8000.")
    }
    setLoading(false)
  }

  return (
    <div className={`app-wrap ${visible ? "visible" : ""}`}>

      {/* Hero */}
      <div className="hero">
        {SRI_LANKA_IMAGES.map((img, i) => (
          <img key={i} src={img.url} alt={img.caption}
            className={`hero-img ${i !== imgIndex ? "fade" : ""}`} />
        ))}
        <div className="hero-overlay" />
        <div className="hero-content">
          <span className="hero-lotus">✿ ✿ ✿</span>
          <h1 className="hero-title">Mahavamsa <span>Explorer</span></h1>
          <p className="hero-sub">Ancient Sri Lankan Chronicle — GraphRAG Intelligence System</p>
          <p className="hero-sinhala">මහාවංශය · ශ්‍රී ලංකාවේ පුරාණ ඉතිහාසය</p>
        </div>
        <div className="hero-caption">{SRI_LANKA_IMAGES[imgIndex].caption}</div>
      </div>

      {/* Stats */}
      {stats && (
        <div className="stats-bar">
          {Object.entries(stats.nodes)
            .filter(([label]) => label !== "null")
            .map(([label, count]) => (
              <div className="stat-item" key={label}>
                <span className="stat-num">{count}</span>
                <span className="stat-label">{label}S</span>
              </div>
            ))}
          <div className="stat-item">
            <span className="stat-num">{stats.relationships}</span>
            <span className="stat-label">Relations</span>
          </div>
        </div>
      )}

      <div className="main">

        {/* Tabs */}
        <div className="tabs">
          {[
            { id: "chat",    label: "✦ Ask the Chronicle" },
            { id: "map",     label: "◎ Sacred Sites" },
            { id: "history", label: "⊕ History" },
          ].map(t => (
            <button key={t.id}
              className={`tab-btn ${activeTab === t.id ? "active" : ""}`}
              onClick={() => setActiveTab(t.id)}>
              {t.label}
            </button>
          ))}
        </div>

        {/* CHAT TAB */}
        {activeTab === "chat" && (
          <>
            {/* Mode selector */}
            <div className="mode-row">
              <span className="mode-label">Mode</span>
              <button
                className={`mode-btn ${mode === "graph" ? "mode-active" : ""}`}
                onClick={() => switchMode("graph")}
              >
                ⬡ GraphRAG
              </button>
              <button
                className={`mode-btn ${mode === "rag" ? "mode-active" : ""}`}
                onClick={() => switchMode("rag")}
              >
                ◈ Baseline RAG
              </button>
              <button
                className={`mode-btn ${mode === "dual_agent" ? "mode-active" : ""}`}
                onClick={() => switchMode("dual_agent")}
              >
                ⚖️ Dual Agent
              </button>
              <span className="mode-hint">
                {mode === "graph"
                  ? "Neo4j knowledge graph"
                  : mode === "rag"
                  ? "ChromaDB semantic search"
                  : "Hybrid graph + text ensemble"}
              </span>
            </div>

            <div className="search-wrap">
              <input className="search-input"
                value={question}
                onChange={e => setQuestion(e.target.value)}
                onKeyDown={e => e.key === "Enter" && askQuestion()}
                placeholder="Ask about kings, battles, temples, or how to visit a place…"
              />
              <button className="search-btn"
                onClick={() => askQuestion()}
                disabled={loading}>
                {loading ? "…" : "Ask"}
              </button>
            </div>

            <div className="suggestions">
              {SUGGESTED.map(s => (
                <button key={s.text} className="sugg-btn"
                  onClick={() => askQuestion(s.text)}>
                  <span>{s.icon}</span>{s.text}
                </button>
              ))}
            </div>

            {loading && (
              <div className="loading-wrap">
                <span className="loading-lotus">✿</span>
                <span className="loading-text">
                  Consulting the ancient chronicle<span className="loading-dots" />
                </span>
              </div>
            )}

            {answer && !loading && (
              <div ref={answerRef}>

                {/* Answer */}
                <div className="answer-box">
                  <div className="answer-header">
                    <div className="answer-mode-dot" />
                    <span className="answer-badge">
                      {mode === "graph"
                        ? "GraphRAG · Knowledge Graph Answer"
                        : mode === "rag"
                        ? "Baseline RAG · Semantic Search Answer"
                        : "Dual Agent · Synthesized Expert Answer"}
                    </span>
                    <span className="answer-mode-tag">
                      {mode === "graph"
                        ? "Neo4j"
                        : mode === "rag"
                        ? "ChromaDB"
                        : "Dual Agent"}
                    </span>
                  </div>
                  <p className="answer-text">{answer}</p>
                </div>

                {/* Translator */}
                <div className="translator-box">
                  <div className="translator-header">
                    <span className="translator-label">🌐 Translate answer</span>
                    <button
                      className="lang-toggle-btn"
                      onClick={() => setShowLangPicker(!showLangPicker)}
                    >
                      {selectedLang ? `✓ ${selectedLang}` : "Choose language"}
                    </button>
                    {selectedLang && (
                      <button
                        className="lang-clear-btn"
                        onClick={() => {
                          setTranslatedAnswer("")
                          setSelectedLang(null)
                          setShowLangPicker(false)
                        }}
                      >
                        ✕ Clear
                      </button>
                    )}
                  </div>

                  {showLangPicker && (
                    <div className="lang-picker">
                      {languages.map(lang => (
                        <button
                          key={lang.code}
                          className="lang-btn"
                          onClick={() => translateAnswer(lang.code, lang.name)}
                        >
                          {lang.flag} {lang.name}
                        </button>
                      ))}
                    </div>
                  )}

                  {translating && (
                    <div className="translating-wrap">
                      <span className="translating-spin">✿</span>
                      Translating to {selectedLang}...
                    </div>
                  )}

                  {translatedAnswer && !translating && (
                    <div className="translated-result">
                      <div className="translated-badge">
                        🌐 {selectedLang} Translation
                      </div>
                      <p className="translated-text">{translatedAnswer}</p>
                    </div>
                  )}
                </div>

                {/* Location card */}
                {highlightSite && (
                  <div className="location-card">
                    <div className="location-icon">📍</div>
                    <div className="location-info">
                      <div className="location-name">{highlightSite.name}</div>
                      <div className="location-sinhala">{highlightSite.sinhala}</div>
                      <div className="location-desc">{highlightSite.description}</div>
                      <div>
                        <a className="gmaps-btn"
                          href={highlightSite.google_maps}
                          target="_blank"
                          rel="noreferrer">
                          🧭 Open in Google Maps
                        </a>
                      </div>
                      <div className="location-coords">
                        📌 {highlightSite.lat}°N, {highlightSite.lng}°E
                      </div>
                    </div>
                  </div>
                )}

                {/* Graph triples — only for GraphRAG */}
                {mode === "graph" && triples.length > 0 && (
                  <div className="triples-box">
                    <div className="triples-header">◈ Knowledge Graph Facts Used</div>
                    {triples.map((t, i) => (
                      <div className="triple-row" key={i}>
                        <span className="triple-subj">{t.subject}</span>
                        <span className="triple-rel">——[{t.relation}]——▶</span>
                        <span className="triple-obj">{t.object}</span>
                      </div>
                    ))}
                  </div>
                )}

              </div>
            )}

            <div className="divider">✦ ✦ ✦</div>
          </>
        )}

        {/* MAP TAB */}
        {activeTab === "map" && (
          <>
            <h2 className="map-title">Sacred Sites of the Mahavamsa</h2>
            <p className="map-sub">Click any marker to see site details and open in Google Maps</p>
            <MapContainer
              center={[7.8731, 80.7718]}
              zoom={8}
              style={{ height: 520, borderRadius: 12, border: "1px solid #3a2e1e" }}
            >
              <TileLayer
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                attribution="© OpenStreetMap contributors"
              />
              {sites.map(site => (
                <Marker key={site.name} position={[site.lat, site.lng]}>
                  <Popup>
                    <div style={{ fontFamily: "Georgia, serif", minWidth: 190 }}>
                      <strong style={{ fontSize: 14, color: "#2c1810" }}>{site.name}</strong>
                      <br />
                      <em style={{ fontSize: 12, color: "#8b6914" }}>{site.sinhala}</em>
                      <br />
                      <span style={{ fontSize: 12, color: "#555", marginTop: 4, display: "block", lineHeight: 1.5 }}>
                        {site.description}
                      </span>
                      <a href={site.google_maps} target="_blank" rel="noreferrer"
                        style={{ display: "inline-block", marginTop: 10, padding: "6px 14px", background: "#1a6b1a", color: "#c8f0c8", borderRadius: 6, fontSize: 12, textDecoration: "none", fontWeight: 600 }}>
                        🧭 Open in Google Maps
                      </a>
                    </div>
                  </Popup>
                </Marker>
              ))}
            </MapContainer>
          </>
        )}

        {/* HISTORY TAB */}
        {activeTab === "history" && (
          <>
            <h2 className="map-title">Your Questions</h2>
            {history.length === 0 ? (
              <div className="empty">
                <span className="empty-lotus">✿</span>
                No questions asked yet. Begin your journey with the chronicle.
              </div>
            ) : (
              history.map((item, i) => (
                <div className="history-item" key={i}>
                  <div className="history-q"><span>✦</span>{item.question}</div>
                  <div className="history-a">
                    {item.answer.slice(0, 220)}{item.answer.length > 220 ? "…" : ""}
                  </div>
                  <div className="history-meta">
                    {item.mode === "graph" ? "⬡ GraphRAG" : "◈ Baseline RAG"} mode
                  </div>
                </div>
              ))
            )}
          </>
        )}

      </div>
    </div>
  )
}