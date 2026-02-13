import React, { useState, useEffect, useRef } from 'react';
import { Upload, FileVideo, Sparkles, Youtube, Instagram, Share2, LogOut, ChevronDown, Check, Activity, LayoutDashboard, Settings, PlusCircle, History, Menu, X, Terminal, Shield, CheckSquare, Square, Play } from 'lucide-react';
import KeyInput from './components/KeyInput';
import MediaInput from './components/MediaInput';
import ResultCard from './components/ResultCard';
import ProcessingAnimation from './components/ProcessingAnimation';
import { getApiUrl } from './config';

// --- Encryption Helpers ---
const SECRET_KEY = import.meta.env.VITE_ENCRYPTION_KEY || "OpenShorts-Static-Salt-Change-Me";
const ENCRYPTION_PREFIX = "ENC:";

const encrypt = (text) => {
  if (!text) return '';
  try {
    const xor = text.split('').map((c, i) =>
      String.fromCharCode(c.charCodeAt(0) ^ SECRET_KEY.charCodeAt(i % SECRET_KEY.length))
    ).join('');
    return ENCRYPTION_PREFIX + btoa(xor);
  } catch (e) {
    console.error("Encryption failed", e);
    return text;
  }
};

const decrypt = (text) => {
  if (!text) return '';
  if (text.startsWith(ENCRYPTION_PREFIX)) {
    try {
      const raw = text.slice(ENCRYPTION_PREFIX.length);
      const xor = atob(raw);
      return xor.split('').map((c, i) =>
        String.fromCharCode(c.charCodeAt(0) ^ SECRET_KEY.charCodeAt(i % SECRET_KEY.length))
      ).join('');
    } catch (e) { return ''; }
  }
  return text;
};

const TikTokIcon = ({ size = 16, className = "" }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" className={className}>
    <path d="M19.589 6.686a4.793 4.793 0 0 1-3.77-4.245V2h-3.445v13.672a2.896 2.896 0 0 1-5.201 1.743l-.002-.001.002.001a2.895 2.895 0 0 1 3.183-4.51v-3.5a6.329 6.329 0 0 0-5.394 10.692 6.33 6.33 0 0 0 10.857-4.424V8.687a8.182 8.182 0 0 0 4.773 1.526V6.79a4.831 4.831 0 0 1-1.003-.104z" />
  </svg>
);

const UserProfileSelector = ({ profiles, selectedUserId, onSelect }) => {
  const [isOpen, setIsOpen] = useState(false);
  if (!profiles || profiles.length === 0) return null;
  const selectedProfile = profiles.find(p => p.username === selectedUserId) || profiles[0];
  return (
    <div className="relative z-50">
      <button onClick={() => setIsOpen(!isOpen)} className="flex items-center justify-between bg-surface border border-white/10 rounded-lg px-3 py-2 text-sm text-zinc-300 hover:bg-white/5 transition-colors min-w-[180px]">
        <span className="flex items-center gap-2">
          <div className="w-5 h-5 rounded-full bg-gradient-to-br from-primary to-purple-600 flex items-center justify-center text-[10px] font-bold text-white">
            {selectedProfile?.username?.substring(0, 1).toUpperCase() || "U"}
          </div>
          <span className="font-medium text-white truncate max-w-[100px]">{selectedProfile?.username || "Select User"}</span>
        </span>
        <ChevronDown size={14} className={`text-zinc-500 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>
      {isOpen && (
        <div className="absolute top-full mt-2 right-0 w-64 bg-[#1a1a1a] border border-white/10 rounded-xl shadow-2xl overflow-hidden">
          <div className="max-h-60 overflow-y-auto custom-scrollbar">
            {profiles.map((profile) => (
              <button key={profile.username} onClick={() => { onSelect(profile.username); setIsOpen(false); }} className="w-full flex items-center justify-between px-4 py-3 hover:bg-white/5 transition-colors text-left group border-b border-white/5 last:border-0">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full bg-gradient-to-br from-primary/20 to-purple-500/20 flex items-center justify-center text-xs font-bold text-white border border-white/10 shrink-0">
                    {profile.username.substring(0, 2).toUpperCase()}
                  </div>
                  <div className="min-w-0">
                    <div className="text-sm font-medium text-zinc-200 group-hover:text-white transition-colors truncate">{profile.username}</div>
                    <div className="flex gap-2 mt-0.5">
                      <div className={`flex items-center gap-1 text-[10px] ${profile.connected.includes('tiktok') ? 'text-zinc-300' : 'text-zinc-600'}`}><TikTokIcon size={10} /></div>
                      <div className={`flex items-center gap-1 text-[10px] ${profile.connected.includes('instagram') ? 'text-pink-400' : 'text-zinc-600'}`}><Instagram size={10} /></div>
                      <div className={`flex items-center gap-1 text-[10px] ${profile.connected.includes('youtube') ? 'text-red-400' : 'text-zinc-600'}`}><Youtube size={10} /></div>
                    </div>
                  </div>
                </div>
                {selectedUserId === profile.username && <Check size={14} className="text-primary shrink-0" />}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

const pollJob = async (jobId) => {
  const res = await fetch(getApiUrl(`/api/status/${jobId}`));
  if (!res.ok) throw new Error('Status check failed');
  return res.json();
};

const formatLogLine = (logEntry) => {
  const match = logEntry.match(/^\[(\d{2}):(\d{2}):(\d{2})\] (.*)/);
  if (match) {
    const [_, h, m, s, text] = match;
    const date = new Date();
    date.setUTCHours(parseInt(h), parseInt(m), parseInt(s));
    const localTime = date.toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
    return `[${localTime}] ${text}`;
  }
  return logEntry;
};

function App() {
  const [apiKey, setApiKey] = useState(localStorage.getItem('gemini_key') || '');
  const [uploadPostKey, setUploadPostKey] = useState(() => {
    const stored = localStorage.getItem('uploadPostKey_v3');
    if (stored) return decrypt(stored);
    return '';
  });

  const [uploadUserId, setUploadUserId] = useState(() => localStorage.getItem('uploadUserId') || '');
  const [userProfiles, setUserProfiles] = useState([]);

  // NEW: Initial state from localStorage to prevent data loss on refresh
  const [jobId, setJobId] = useState(() => localStorage.getItem('current_job_id') || null);

  const [status, setStatus] = useState('idle');
  const [results, setResults] = useState(null);
  const [logs, setLogs] = useState([]);
  const [logsVisible, setLogsVisible] = useState(true);
  const [processingMedia, setProcessingMedia] = useState(null);
  const [activeTab, setActiveTab] = useState('dashboard');
  const [selectedIndices, setSelectedIndices] = useState([]);

  const [syncedTime, setSyncedTime] = useState(0);
  const [isSyncedPlaying, setIsSyncedPlaying] = useState(false);
  const [syncTrigger, setSyncTrigger] = useState(0);

  const logsEndRef = useRef(null);
  const logsContainerRef = useRef(null);
  const [shouldAutoScroll, setShouldAutoScroll] = useState(true);

  // NEW: State to store clips fetched from the Google Sheet API
  const [videoClips, setVideoClips] = useState([]);


  // --- Handlers ---
  const handleClipPlay = (startTime) => {
    setSyncedTime(startTime);
    setIsSyncedPlaying(true);
    setSyncTrigger(prev => prev + 1);
  };

  const handleClipPause = () => { setIsSyncedPlaying(false); };

  const handleProcess = async (data) => {
    setStatus('processing');
    setLogs(["🚀 Starting analysis..."]);
    setResults(null);
    setProcessingMedia(data);
    setShouldAutoScroll(true);
    try {
      let body;
      const headers = { 'X-Gemini-Key': apiKey };
      if (data.type === 'url') {
        headers['Content-Type'] = 'application/json';
        body = JSON.stringify({ url: data.payload, style: data.style });
      } else {
        const formData = new FormData();
        formData.append('file', data.payload);
        formData.append('style', data.style);
        body = formData;
      }
      const res = await fetch(getApiUrl('/api/analyze'), {
        method: 'POST',
        headers: data.type === 'url' ? headers : { 'X-Gemini-Key': apiKey },
        body
      });
      if (!res.ok) throw new Error(await res.text());
      const resData = await res.json();
      setJobId(resData.job_id); // This triggers localStorage save via useEffect
    } catch (e) {
      setStatus('error');
      setLogs(l => [...l, `Error starting job: ${e.message}`]);
    }
  };

  const handleGenerateSelected = async () => {
    if (selectedIndices.length === 0) return alert("Select at least one clip.");
    setStatus('processing');
    setLogs(l => [...l, `🎬 Generating ${selectedIndices.length} selected clips...`]);
    try {
      const res = await fetch(getApiUrl('/api/generate-selected'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ job_id: jobId, selected_indices: selectedIndices })
      });
      if (!res.ok) throw new Error("Request failed (Backend might be restarting)");
    } catch (e) {
      setStatus('error');
      setLogs(l => [...l, `Error: ${e.message}`]);
    }
  };

  const toggleSelection = (index) => {
    setSelectedIndices(prev => prev.includes(index) ? prev.filter(i => i !== index) : [...prev, index]);
  };

  const handleReset = () => {
    setStatus('idle');
    setJobId(null);
    localStorage.removeItem('current_job_id'); // Clear from storage
    setResults(null);
    setLogs([]);
    setProcessingMedia(null);
    setSelectedIndices([]);
    setShouldAutoScroll(true);
    setVideoClips([]); // Clear video clips on reset
  };

  const fetchUserProfiles = async () => {
    if (!uploadPostKey) return;
    try {
      const res = await fetch(getApiUrl('/api/social/user'), { headers: { 'X-Upload-Post-Key': uploadPostKey } });
      if (!res.ok) throw new Error("Failed");
      const data = await res.json();
      if (data.profiles?.length > 0) {
        setUserProfiles(data.profiles);
        if (!uploadUserId) setUploadUserId(data.profiles[0].username);
      } else alert("No profiles found.");
    } catch (e) { alert("Check API Key."); }
  };

  // --- Effects ---
  useEffect(() => { if (apiKey) localStorage.setItem('gemini_key', apiKey); }, [apiKey]);
  useEffect(() => {
    if (uploadPostKey) localStorage.setItem('uploadPostKey_v3', encrypt(uploadPostKey));
    if (uploadUserId) localStorage.setItem('uploadUserId', uploadUserId);
  }, [uploadPostKey, uploadUserId]);
  useEffect(() => { if (uploadPostKey && userProfiles.length === 0) fetchUserProfiles(); }, [uploadPostKey]);

  // NEW: Save Job ID to LocalStorage whenever it changes
  useEffect(() => {
    if (jobId) localStorage.setItem('current_job_id', jobId);
  }, [jobId]);

  // If we have a stored Job ID on load, set status to processing so it polls immediately
  useEffect(() => {
    if (jobId && status === 'idle') {
      setStatus('processing');
      setLogs(["🔄 Restoring previous session..."]);
    }
  }, []); // Run once on mount

  useEffect(() => {
    const checkServerConfig = async () => {
      if (apiKey) return;
      try {
        const res = await fetch(getApiUrl('/api/config'));
        if (res.ok && (await res.json()).has_gemini_key) {
          setApiKey("MANAGED_BY_SERVER");
          console.log("✅ Using Server-Side Gemini Key");
        }
      } catch (e) { }
    };
    checkServerConfig();
  }, []);

  useEffect(() => {
    let interval;
    if ((status === 'processing' || status === 'completed' || status === 'analyzed') && jobId) {
      interval = setInterval(async () => {
        try {
          const data = await pollJob(jobId);
          if (data.result) setResults(data.result);
          if (data.logs) setLogs(data.logs);

          if (data.status === 'analyzed' && status !== 'analyzed') {
            setStatus('analyzed');
            if (data.result?.shorts) {
              const count = Math.min(3, data.result.shorts.length);
              setSelectedIndices([...Array(count).keys()]);
            }
          } else if (data.status === 'completed' && status !== 'complete') {
            setStatus('complete');
          } else if (data.status === 'failed') {
            setStatus('error');
          }
        } catch (e) {
          // If polling fails (504), do NOT set error state immediately. 
          // The backend might be restarting. Just log it.
          console.log("Polling failed, retrying...");
        }
      }, 2000);
    }
    return () => clearInterval(interval);
  }, [status, jobId]);

  // Effect to fetch video clips from the backend
  useEffect(() => {
    const fetchVideoClips = async () => {
      if (status === 'complete' && processingMedia?.videoTitle) {
        try {
          const res = await fetch(getApiUrl(`/api/clips/${processingMedia.videoTitle}`));
          if (!res.ok) throw new Error("Failed to fetch video clips");
          const data = await res.json();
          setVideoClips(data.clips);
          setLogs(l => [...l, `📊 Fetched ${data.clips.length} clips from Google Sheet.`]);
        } catch (e) {
          setLogs(l => [...l, `❌ Error fetching video clips from Google Sheet: ${e.message}`]);
        }
      }
    };
    fetchVideoClips();
  }, [status, processingMedia]);


  useEffect(() => {
    if (shouldAutoScroll && logsEndRef.current) logsEndRef.current.scrollIntoView({ behavior: "smooth" });
  }, [logs, shouldAutoScroll, logsVisible]);

  const handleLogsScroll = () => {
    if (!logsContainerRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = logsContainerRef.current;
    setShouldAutoScroll(scrollHeight - scrollTop - clientHeight < 50);
  };

  // --- Render (Same as before) ---
  const Sidebar = () => (
    <div className="w-20 lg:w-64 bg-surface border-r border-white/5 flex flex-col h-full shrink-0 transition-all duration-300">
      <div className="p-6 flex items-center gap-3">
        <div className="w-8 h-8 bg-white/5 rounded-lg flex items-center justify-center shrink-0 overflow-hidden border border-white/5">
          <img src="/logo-openshorts.png" alt="Logo" className="w-full h-full object-cover" />
        </div>
        <span className="font-bold text-lg text-white hidden lg:block tracking-tight">OpenShorts</span>
      </div>
      <nav className="flex-1 px-4 py-4 space-y-2">
        <button onClick={() => setActiveTab('dashboard')} className={`w-full flex items-center gap-3 px-3 py-3 rounded-xl transition-colors ${activeTab === 'dashboard' ? 'bg-primary/10 text-primary' : 'text-zinc-400 hover:text-white hover:bg-white/5'}`}>
          <LayoutDashboard size={20} /> <span className="font-medium hidden lg:block">Dashboard</span>
        </button>
        <button onClick={() => setActiveTab('settings')} className={`w-full flex items-center gap-3 px-3 py-3 rounded-xl transition-colors ${activeTab === 'settings' ? 'bg-primary/10 text-primary' : 'text-zinc-400 hover:text-white hover:bg-white/5'}`}>
          <Settings size={20} /> <span className="font-medium hidden lg:block">Settings</span>
        </button>
      </nav>
      <div className="p-4 border-t border-white/5">
        <div className="flex items-center gap-2 p-3 bg-white/5 rounded-xl"><span className="text-xs text-zinc-500">v2.1 (Auto-Recovery)</span></div>
      </div>
    </div>
  );

  return (
    <div className="flex h-screen bg-background overflow-hidden selection:bg-primary/30">
      <Sidebar />
      <main className="flex-1 flex flex-col h-full overflow-hidden relative">
        <div className="absolute inset-0 overflow-hidden -z-10 pointer-events-none">
          <div className="absolute -top-[10%] -right-[10%] w-[50%] h-[50%] bg-primary/5 rounded-full blur-[120px]" />
        </div>

        <header className="h-16 border-b border-white/5 bg-background/50 backdrop-blur-md flex items-center justify-between px-6 shrink-0 z-10">
          <div className="flex items-center gap-4">
            {status !== 'idle' && (
              <button onClick={handleReset} className="flex items-center gap-2 text-sm text-zinc-400 hover:text-white transition-colors">
                <PlusCircle size={16} /> <span className="hidden sm:inline">New Project</span>
              </button>
            )}
          </div>
          <div className="flex items-center gap-4">
            {userProfiles.length > 0 && <UserProfileSelector profiles={userProfiles} selectedUserId={uploadUserId} onSelect={setUploadUserId} />}
            {!apiKey && <span className="text-xs text-amber-500 bg-amber-500/10 px-3 py-1 rounded-full border border-amber-500/20">API Key Missing</span>}
          </div>
        </header>

        <div className="flex-1 overflow-hidden relative">

          {activeTab === 'settings' && (
            <div className="h-full overflow-y-auto p-8 max-w-2xl mx-auto animate-[fadeIn_0.3s_ease-out]">
              <div className="flex items-center justify-between mb-8">
                <h1 className="text-2xl font-bold">Settings</h1>
                <div className="px-3 py-1 bg-green-500/10 border border-green-500/20 rounded-full text-[10px] text-green-400 font-medium flex items-center gap-2">
                  <Shield size={12} /> Privacy: keys only live in your browser
                </div>
              </div>
              <KeyInput onKeySet={setApiKey} savedKey={apiKey} />
              <div className="glass-panel p-6 mt-8">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-lg font-semibold">Social Integration</h2>
                  <span className="text-[10px] bg-white/5 border border-white/5 px-2 py-0.5 rounded text-zinc-500 uppercase tracking-wider">Optional</span>
                </div>
                <div className="space-y-4">
                  <label className="block text-sm text-zinc-400">Upload-Post API Key</label>
                  <div className="flex gap-2">
                    <input type="password" value={uploadPostKey} onChange={(e) => setUploadPostKey(e.target.value)} className="input-field" placeholder="ey..." />
                    <button onClick={fetchUserProfiles} className="btn-primary py-2 px-4 text-sm">Connect</button>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'dashboard' && status === 'idle' && (
            <div className="h-full flex flex-col items-center justify-center p-6 animate-[fadeIn_0.3s_ease-out]">
              <div className="max-w-xl w-full text-center space-y-8">
                <div className="space-y-4">
                  <h1 className="text-4xl md:text-5xl font-black bg-gradient-to-b from-white to-white/60 bg-clip-text text-transparent">Create Viral Shorts</h1>
                  <p className="text-zinc-400 text-lg">Paste a link, review AI scripts, and generate.</p>
                </div>
                <MediaInput onProcess={handleProcess} isProcessing={status === 'processing'} />
              </div>
            </div>
          )}

          {activeTab === 'dashboard' && status !== 'idle' && (
            <div className="h-full flex flex-col md:flex-row animate-[fadeIn_0.3s_ease-out]">
              <div className="w-full md:w-[40%] h-full flex flex-col border-r border-white/5 bg-black/20 p-6 overflow-hidden transition-all duration-700">
                <div className="mb-6 flex items-center justify-between">
                  <h2 className="text-lg font-semibold flex items-center gap-2">
                    <Activity className={`text-primary ${status === 'processing' ? 'animate-pulse' : ''}`} size={20} />
                    Live Status
                  </h2>
                  <span className={`text-xs px-2 py-1 rounded-full border bg-primary/10 border-primary/20 text-primary`}>
                    {status.toUpperCase()}
                  </span>
                </div>
                <div className="aspect-video bg-black rounded-xl border border-white/10 overflow-hidden mb-4 relative shadow-2xl">
                  <ProcessingAnimation media={processingMedia} isComplete={status === 'complete' || status === 'analyzed'} syncedTime={syncedTime} isSyncedPlaying={isSyncedPlaying} syncTrigger={syncTrigger} />
                  {status === 'analyzed' && (
                    <div className="absolute inset-0 flex items-center justify-center bg-black/60 backdrop-blur-sm z-50">
                      <div className="text-center">
                        <Check size={48} className="mx-auto text-green-400 mb-2" />
                        <p className="font-bold text-white">Analysis Complete</p>
                        <p className="text-xs text-zinc-400">Select clips on the right to generate.</p>
                      </div>
                    </div>
                  )}
                </div>
                <div className="bg-[#0c0c0e] rounded-xl border border-white/10 overflow-hidden flex flex-col flex-1 min-h-0">
                  <div className="px-4 py-2 border-b border-white/5 flex items-center justify-between bg-white/5 shrink-0">
                    <span className="text-xs font-mono text-zinc-400 flex items-center gap-2"><Terminal size={12} /> System Logs</span>
                    <button onClick={() => setLogsVisible(!logsVisible)} className="text-zinc-500 hover:text-white transition-colors">
                      {logsVisible ? <ChevronDown size={14} /> : <ChevronDown size={14} className="rotate-180" />}
                    </button>
                  </div>
                  {logsVisible && (
                    <div ref={logsContainerRef} onScroll={handleLogsScroll} className="flex-1 p-4 overflow-y-auto font-mono text-xs space-y-1.5 custom-scrollbar text-zinc-400">
                      {logs.map((log, i) => <div key={i} className={log.toLowerCase().includes('error') ? 'text-red-400' : ''}>{formatLogLine(log)}</div>)}
                      <div ref={logsEndRef} />
                    </div>
                  )}
                </div>
              </div>

              <div className="w-full md:w-[60%] h-full bg-background p-6 flex flex-col overflow-hidden">
                {status === 'analyzed' && results?.shorts && (
                  <div className="flex flex-col h-full animate-[fadeIn_0.3s_ease-out]">
                    <div className="flex items-center justify-between mb-6 shrink-0">
                      <div>
                        <h2 className="text-2xl font-bold text-white flex items-center gap-2">
                          <Sparkles className="text-yellow-400" /> Review Scripts
                        </h2>
                        <p className="text-sm text-zinc-400">AI found {results.shorts.length} potential viral moments.</p>
                      </div>
                      <button onClick={handleGenerateSelected} className="bg-primary hover:bg-primary/90 text-black font-bold py-2 px-6 rounded-lg transition-all flex items-center gap-2 shadow-lg shadow-primary/20">
                        Generate {selectedIndices.length} Clips <Play size={16} fill="currentColor" />
                      </button>
                    </div>
                    <div className="flex-1 overflow-y-auto custom-scrollbar pr-2 space-y-3">
                      {results.shorts.map((clip, i) => (
                        <div key={i} onClick={() => toggleSelection(i)} className={`p-4 rounded-xl border transition-all cursor-pointer group relative overflow-hidden ${selectedIndices.includes(i) ? 'bg-primary/5 border-primary/50' : 'bg-white/5 border-white/5 hover:border-white/20'}`}>
                          <div className="flex items-start gap-4 relative z-10">
                            <div className={`mt-1 transition-colors ${selectedIndices.includes(i) ? 'text-primary' : 'text-zinc-600'}`}>{selectedIndices.includes(i) ? <CheckSquare size={24} /> : <Square size={24} />}</div>
                            <div className="flex-1 space-y-2">
                              <div className="flex items-center justify-between">
                                <h3 className="font-bold text-white text-base">{clip.video_title_for_youtube_short || "Untitled Clip"}</h3>
                                {clip.viral_score && <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold border ${clip.viral_score >= 8 ? 'bg-green-500/10 text-green-400 border-green-500/20' : 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20'}`}>SCORE: {clip.viral_score}/10</span>}
                              </div>
                              <div className="p-3 bg-black/40 rounded-lg border border-white/5 group-hover:border-white/10 transition-colors">
                                <p className="text-sm text-zinc-300 font-mono leading-relaxed opacity-90">"{clip.script || "No script available..."}"</p>
                              </div>
                              <div className="flex items-center gap-4 text-[10px] text-zinc-500 font-mono">
                                <span>⏱ {clip.start}s - {clip.end}s</span>
                                {clip.reasoning && <span className="text-zinc-400">• {clip.reasoning}</span>}
                              </div>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                {/* --- RESULTS VIEW (Complete) --- */}
                {(status === 'complete' || (status === 'processing' && (results?.clips && results.clips.length > 0 || videoClips.length > 0))) && (
                  <div className="flex flex-col h-full animate-[fadeIn_0.3s_ease-out]">
                    <h2 className="text-lg font-semibold mb-6 flex items-center gap-2 shrink-0">
                      <Sparkles className="text-yellow-400" size={20} /> Generated Shorts
                      {/* Display count from backend-fetched clips if available, otherwise from results */}
                      {(results?.clips?.length > 0 || videoClips.length > 0) && (
                        <span className="text-xs bg-white/10 text-white px-2 py-0.5 rounded-full ml-auto flex items-center gap-2">
                          {status === 'processing' && <span className="w-2 h-2 bg-primary rounded-full animate-pulse" />}
                          {videoClips.length > 0 ? videoClips.length : results.clips.length} Clips Ready
                        </span>
                      )}
                    </h2>
                    <div className="flex-1 overflow-y-auto custom-scrollbar p-1">
                      {/* CHANGED: 1 column default ensures wide cards are not squished. 2 columns only on huge screens. */}
                      <div className="grid grid-cols-1 2xl:grid-cols-2 gap-6 pb-10">
                        {(videoClips.length > 0 ? videoClips : results.clips).map((clip, i) => (
                          <ResultCard
                            key={clip["Clip ID"] || i} // Use Clip ID from sheet or index
                            clip={clip}
                            index={i}
                            jobId={jobId}
                            uploadPostKey={uploadPostKey}
                            uploadUserId={uploadUserId}
                            geminiApiKey={apiKey}
                            onPlay={(time) => handleClipPlay(time)}
                            onPause={handleClipPause}
                          />
                        ))}
                        {status === 'processing' && (
                          <div className="h-64 rounded-2xl border-2 border-dashed border-white/10 flex flex-col items-center justify-center text-zinc-500 bg-white/5 animate-pulse">
                            <div className="w-8 h-8 border-2 border-zinc-600 border-t-primary rounded-full animate-spin mb-2" />
                            <span className="text-xs">Generating next clip...</span>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                )}

                {/* --- PROCESSING LOADER (Initial) --- */}
                {status === 'processing' && !results?.clips && (
                  <div className="h-full flex flex-col items-center justify-center text-zinc-500 space-y-4 opacity-50">
                    <div className="w-12 h-12 rounded-full border-2 border-zinc-800 border-t-primary animate-spin" />
                    <p className="text-sm">Processing content...</p>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

export default App;
