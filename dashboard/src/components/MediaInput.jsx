import React, { useState, useEffect } from 'react';
import { Upload, Link, ArrowRight, FileVideo, Palette, ChevronDown } from 'lucide-react';
import { getApiUrl } from '../config';

const MediaInput = ({ onProcess, isProcessing }) => {
  const [url, setUrl] = useState('');
  const [file, setFile] = useState(null);
  const [dragActive, setDragActive] = useState(false);
  const [styles, setStyles] = useState(['original']);
  const [selectedStyle, setSelectedStyle] = useState('original');

  useEffect(() => {
    fetch(getApiUrl('/api/styles'))
      .then(res => res.json())
      .then(data => {
        if (data.styles) {
          setStyles(data.styles);
          if (data.styles.length > 0) setSelectedStyle(data.styles[0]);
        }
      })
      .catch(err => console.error("Failed to fetch styles", err));
  }, []);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (url) onProcess({ type: 'url', payload: url, style: selectedStyle });
    else if (file) onProcess({ type: 'file', payload: file, style: selectedStyle });
  };

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") setDragActive(true);
    else if (e.type === "dragleave") setDragActive(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFile(e.dataTransfer.files[0]);
    }
  };

  return (
    <div className="w-full max-w-2xl mx-auto space-y-6">
      <div className="flex gap-4 p-1 bg-white/5 rounded-xl border border-white/10">
        <button className="flex-1 py-2 text-sm font-medium text-white bg-white/10 rounded-lg shadow-sm">
          <Link size={16} className="inline mr-2" /> YouTube URL
        </button>
      </div>

      <div className="flex items-center gap-3 p-4 bg-white/5 rounded-xl border border-white/10">
        <div className="p-2 bg-primary/10 rounded-lg">
          <Palette size={18} className="text-primary" />
        </div>
        <div className="flex-1">
          <label className="text-[10px] uppercase tracking-wider text-zinc-500 font-bold block mb-1">Select Edit Style</label>
          <select
            value={selectedStyle}
            onChange={(e) => setSelectedStyle(e.target.value)}
            className="w-full bg-transparent text-white text-sm focus:outline-none cursor-pointer appearance-none"
          >
            {styles.map(s => (
              <option key={s} value={s} className="bg-[#1a1a1a] text-white">
                {s.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ')}
              </option>
            ))}
          </select>
        </div>
        <div className="text-zinc-600">
          <ChevronDown size={16} />
        </div>
      </div>

      <form onSubmit={handleSubmit} className="relative">
        <div className="relative group">
          <div className="absolute -inset-0.5 bg-gradient-to-r from-primary to-purple-600 rounded-xl blur opacity-20 group-hover:opacity-40 transition duration-500"></div>
          <input
            type="text"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="Paste YouTube URL here..."
            className="relative w-full bg-[#0c0c0e] text-white border border-white/10 rounded-xl py-4 pl-6 pr-32 focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/50 transition-all shadow-xl"
            disabled={isProcessing}
          />
          <button
            type="submit"
            disabled={!url && !file || isProcessing}
            className="absolute right-2 top-2 bottom-2 bg-white text-black font-bold py-2 px-6 rounded-lg hover:bg-zinc-200 disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center gap-2"
          >
            {isProcessing ? 'Analyzing...' : 'Analyze'} <ArrowRight size={16} />
          </button>
        </div>
      </form>

      {/* File Upload Area */}
      <div
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        className={`border-2 border-dashed rounded-xl p-8 text-center transition-all ${dragActive ? 'border-primary bg-primary/5' : 'border-white/10 hover:border-white/20 hover:bg-white/5'
          }`}
      >
        <div className="flex flex-col items-center gap-3">
          <div className="w-12 h-12 rounded-full bg-white/5 flex items-center justify-center">
            <Upload size={20} className="text-zinc-400" />
          </div>
          <p className="text-sm text-zinc-400">
            {file ? (
              <span className="text-white font-medium flex items-center gap-2">
                <FileVideo size={16} /> {file.name}
              </span>
            ) : (
              "Or drop a video file here"
            )}
          </p>
        </div>
      </div>
    </div>
  );
};

export default MediaInput;
