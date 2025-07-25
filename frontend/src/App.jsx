import { useState } from "react";

function App() {
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(false);
  const [scraping, setScraping] = useState(false);
  const [scrapeDone, setScrapeDone] = useState(false);
  const [error, setError] = useState("");
  const [logs, setLogs] = useState([]);
  const [searchTerm, setSearchTerm] = useState("");

  const fetchProjects = () => {
    setLoading(true);
    setError("");

    fetch("https://webscrap-0j33.onrender.com/api/projects")
      .then((res) => {
        if (!res.ok) throw new Error("Failed to fetch");
        return res.json();
      })
      .then((data) => {
        setProjects(data);
        setLoading(false);
      })
      .catch((err) => {
        console.error(err);
        setError("❌ Failed to load project data.");
        setLoading(false);
      });
  };

  const startScraping = () => {
    setScraping(true);
    setScrapeDone(false);
    setError("");
    setLogs([]);
    setProjects([]);
    setLoading(false);

    const eventSource = new EventSource("https://webscrap-0j33.onrender.com/api/scrape");

    eventSource.onmessage = (event) => {
      setLogs((prev) => [...prev, event.data]);
    };

    eventSource.onerror = (err) => {
      console.error("SSE error", err);
      setError("❌ Scraping failed.");
      setScraping(false);
      eventSource.close();
    };

    eventSource.addEventListener("done", () => {
      eventSource.close();
      setScraping(false);
      setScrapeDone(true);
      fetchProjects();
    });
  };

  const handleDownload = () => {
    window.open("https://webscrap-0j33.onrender.com/api/download", "_blank");
  };

  const filteredProjects = projects.filter((project) => {
    const name = project["BUIDL name"]?.toLowerCase() || "";
    const org = project["Org"]?.toLowerCase() || "";
    return (
      name.includes(searchTerm.toLowerCase()) ||
      org.includes(searchTerm.toLowerCase())
    );
  });

  return (
    <main className="min-h-screen bg-gray-50 px-6 py-10">
      <header className="text-center mb-10">
        <h1 className="text-3xl font-bold text-blue-700">🚀 DoraHacks Project Explorer</h1>
        <p className="text-gray-600">Live list of BUIDLs and their organizations</p>
      </header>
  
      <div className="flex justify-center gap-4 mb-8 flex-wrap">
        <button
          onClick={startScraping}
          disabled={scraping}
          className="bg-blue-600 text-white px-4 py-2 rounded disabled:opacity-50"
        >
          {scraping ? "⏳ Scraping..." : "🔄 Start Scraping"}
        </button>
  
        {scrapeDone && (
          <button
            onClick={handleDownload}
            className="bg-green-600 text-white px-4 py-2 rounded"
          >
            ⬇️ Download Excel
          </button>
        )}
      </div>
  
      {logs.length > 0 && (
        <div className="bg-black text-green-400 p-4 rounded font-mono text-sm max-h-80 overflow-auto mb-6">
          {logs.map((line, index) => (
            <div key={index}>{line}</div>
          ))}
        </div>
      )}
  
      {/* 🔍 Move search input here, just above the projects */}
      {scrapeDone && projects.length > 0 && (
        <div className="mb-6 flex justify-center">
          <input
            type="text"
            placeholder="🔍 Search by name or organization..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="border border-gray-300 rounded px-4 py-2 w-full max-w-md"
          />
        </div>
      )}
  
      {loading && (
        <div className="text-center text-lg text-gray-600">⏳ Loading projects...</div>
      )}
  
      {error && (
        <div className="text-center text-red-500 font-semibold">{error}</div>
      )}
  
      {!loading && !error && scrapeDone && projects.length === 0 && (
        <div className="text-center text-gray-500">No projects found.</div>
      )}
  
      {!loading && !error && filteredProjects.length > 0 && (
        <div className="grid gap-6 sm:grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
          {filteredProjects.map((project) => (
            <div
              key={project["BUIDL ID"]}
              className="bg-white p-5 rounded-xl shadow hover:shadow-md transition-all"
            >
              <h2 className="text-xl font-bold text-gray-800 mb-1">
                {project["BUIDL name"] || "Unnamed Project"}
              </h2>
              <p className="text-sm text-gray-600">
                Org: <span className="font-medium">{project["Org"] || "N/A"}</span>
              </p>
              <a
                href={project["BUIDL profile"]}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-block mt-3 text-sm text-blue-600 hover:underline"
              >
                🔗 View on DoraHacks
              </a>
            </div>
          ))}
        </div>
      )}
    </main>
  );  
}
export default App;
