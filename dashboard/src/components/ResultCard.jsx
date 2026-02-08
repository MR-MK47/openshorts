import React, { useState, useEffect } from 'react';
import { Download, Share2, Instagram, Youtube, Video, CheckCircle, AlertCircle, X, Loader2, Copy, Wand2, Type, Calendar, Clock, Play, Pause } from 'lucide-react';
import { getApiUrl } from '../config';
import SubtitleModal from './SubtitleModal';

export default function ResultCard({ clip, index, jobId, uploadPostKey, uploadUserId, geminiApiKey, onPlay, onPause }) {
    const [showModal, setShowModal] = useState(false);
    const [showSubtitleModal, setShowSubtitleModal] = useState(false);
    const videoRef = React.useRef(null);
    const [currentVideoUrl, setCurrentVideoUrl] = useState(getApiUrl(clip.video_url));
    const [isPlaying, setIsPlaying] = useState(false);

    const [platforms, setPlatforms] = useState({
        tiktok: true,
        instagram: true,
        youtube: true
    });
    const [postTitle, setPostTitle] = useState("");
    const [postDescription, setPostDescription] = useState("");
    const [isScheduling, setIsScheduling] = useState(false);
    const [scheduleDate, setScheduleDate] = useState("");

    const [posting, setPosting] = useState(false);
    const [postResult, setPostResult] = useState(null);

    const [isEditing, setIsEditing] = useState(false);
    const [isSubtitling, setIsSubtitling] = useState(false);
    const [editError, setEditError] = useState(null);

    useEffect(() => {
        if (showModal) {
            setPostTitle(clip.video_title_for_youtube_short || "Viral Short");
            setPostDescription(clip.video_description_for_instagram || clip.video_description_for_tiktok || "");
            setIsScheduling(false);
            setScheduleDate("");
            setPostResult(null);
        }
    }, [showModal, clip]);

    const handleAutoEdit = async () => {
        setIsEditing(true);
        setEditError(null);
        try {
             const apiKey = geminiApiKey || localStorage.getItem('gemini_key');
             if (!apiKey) throw new Error("Gemini API Key is missing. Please set it in Settings.");

             const res = await fetch(getApiUrl('/api/edit'), {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'X-Gemini-Key': apiKey 
                },
                body: JSON.stringify({
                    job_id: jobId,
                    clip_index: index,
                    input_filename: currentVideoUrl.split('/').pop()
                })
             });

             if (!res.ok) {
                 const errText = await res.text();
                 try {
                     const jsonErr = JSON.parse(errText);
                     throw new Error(jsonErr.detail || errText);
                 } catch (e) {
                     throw new Error(errText);
                 }
             }

             const data = await res.json();
             if (data.new_video_url) {
                 const newUrl = getApiUrl(data.new_video_url);
                 // Add timestamp to force reload
                 setCurrentVideoUrl(`${newUrl}?t=${Date.now()}`);
                 if (videoRef.current) {
                     videoRef.current.load();
                 }
             }

        } catch (e) {
            setEditError(e.message);
            setTimeout(() => setEditError(null), 5000);
        } finally {
            setIsEditing(false);
        }
    };

    const handleSubtitle = async (options) => {
        setIsSubtitling(true);
        setEditError(null);
        try {
            const res = await fetch(getApiUrl('/api/subtitle'), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    job_id: jobId,
                    clip_index: index,
                    position: options.position,
                    font_size: options.fontSize,
                    input_filename: currentVideoUrl.split('/').pop()
                })
            });

            if (!res.ok) {
                const errText = await res.text();
                throw new Error(errText);
            }

            const data = await res.json();
            if (data.new_video_url) {
                const newUrl = getApiUrl(data.new_video_url);
                setCurrentVideoUrl(`${newUrl}?t=${Date.now()}`);
                if (videoRef.current) {
                    videoRef.current.load();
                }
                setShowSubtitleModal(false);
            }

        } catch (e) {
            setEditError(e.message);
            setTimeout(() => setEditError(null), 5000);
        } finally {
            setIsSubtitling(false);
        }
    };

    const handlePost = async () => {
        if (!uploadPostKey || !uploadUserId) {
            setPostResult({ success: false, msg: "Missing API Key or User ID." });
            return;
        }

        const selectedPlatforms = Object.keys(platforms).filter(k => platforms[k]);
        if (selectedPlatforms.length === 0) {
            setPostResult({ success: false, msg: "Select at least one platform." });
            return;
        }

        if (isScheduling && !scheduleDate) {
            setPostResult({ success: false, msg: "Please select a date and time." });
            return;
        }

        setPosting(true);
        setPostResult(null);

        try {
            const payload = {
                job_id: jobId,
                clip_index: index,
                api_key: uploadPostKey,
                user_id: uploadUserId,
                platforms: selectedPlatforms,
                title: postTitle,
                description: postDescription
            };

            if (isScheduling && scheduleDate) {
                payload.scheduled_date = new Date(scheduleDate).toISOString();
                payload.timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
            }

            const res = await fetch(getApiUrl('/api/social/post'), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (!res.ok) {
                const errText = await res.text();
                try {
                    const jsonErr = JSON.parse(errText);
                    throw new Error(jsonErr.detail || errText);
                } catch (e) {
                    throw new Error(errText);
                }
            }

            setPostResult({ success: true, msg: isScheduling ? "Scheduled successfully!" : "Posted successfully!" });
            setTimeout(() => {
                setShowModal(false);
                setPostResult(null);
            }, 3000);

        } catch (e) {
            setPostResult({ success: false, msg: `Failed: ${e.message}` });
        } finally {
            setPosting(false);
        }
    };

    const togglePlay = () => {
        if (videoRef.current) {
            if (isPlaying) {
                videoRef.current.pause();
                onPause && onPause();
            } else {
                videoRef.current.play();
                onPlay && onPlay(clip.start);
            }
            setIsPlaying(!isPlaying);
        }
    };

    return (
        <div className="bg-[#1a1a1a] border border-white/5 rounded-2xl overflow-hidden flex flex-col hover:border-white/10 transition-all animate-[fadeIn_0.5s_ease-out] shadow-xl">
            
            {/* 1. Video Section (Full Width on Mobile, Side by Side isn't ideal for vertical video unless wide container) */}
            {/* We will stick to the Vertical Card layout you like but make it "roomy" */}
            <div className="relative aspect-[9/16] bg-black group/video">
                <video
                    ref={videoRef}
                    src={currentVideoUrl}
                    className="w-full h-full object-contain bg-black"
                    playsInline
                    onClick={togglePlay}
                    onPlay={() => setIsPlaying(true)}
                    onPause={() => setIsPlaying(false)}
                    onEnded={() => setIsPlaying(false)}
                />
                
                {/* Play Button Overlay */}
                {!isPlaying && (
                    <div className="absolute inset-0 flex items-center justify-center bg-black/20 cursor-pointer" onClick={togglePlay}>
                        <div className="w-14 h-14 rounded-full bg-white/10 backdrop-blur-md flex items-center justify-center border border-white/20 transition-transform hover:scale-110">
                            <Play size={24} fill="white" className="ml-1" />
                        </div>
                    </div>
                )}

                {/* Badge Overlay */}
                <div className="absolute top-3 left-3">
                    <span className="bg-black/60 backdrop-blur-md text-white text-[10px] font-bold px-2 py-1 rounded-md border border-white/10 uppercase tracking-wide">
                        Clip {index + 1}
                    </span>
                </div>
                
                {isEditing && (
                    <div className="absolute inset-0 bg-black/70 backdrop-blur-sm flex flex-col items-center justify-center z-10 p-4 text-center">
                        <Loader2 size={32} className="text-primary animate-spin mb-3" />
                        <span className="text-xs font-bold text-white uppercase tracking-wider">AI Magic...</span>
                    </div>
                )}
            </div>

            {/* 2. Details Section (Below Video) */}
            <div className="flex-1 p-5 flex flex-col bg-[#121214] gap-4">
                
                {/* Title & Tags */}
                <div>
                     <h3 className="text-base font-bold text-white leading-tight line-clamp-2 mb-2" title={clip.video_title_for_youtube_short}>
                        {clip.video_title_for_youtube_short || "Viral Clip Generated"}
                    </h3>
                    <div className="flex flex-wrap gap-2 text-[10px] text-zinc-500 font-mono">
                        <span className="bg-white/5 px-2 py-1 rounded border border-white/5">{Math.floor(clip.end - clip.start)}s</span>
                        {clip.viral_score && <span className={`px-2 py-1 rounded border ${clip.viral_score>=8 ? 'bg-green-500/10 text-green-400 border-green-500/20' : 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20'}`}>Score: {clip.viral_score}</span>}
                    </div>
                </div>

                {/* Data Fields */}
                <div className="flex-1 space-y-3">
                     {/* YouTube Field */}
                     <div className="bg-black/20 rounded-lg p-3 border border-white/5 hover:border-white/10 transition-colors">
                        <div className="flex items-center gap-2 text-[10px] font-bold text-red-400 mb-1.5 uppercase tracking-wider">
                            <Youtube size={12} /> YouTube Title
                        </div>
                        <p className="text-xs text-zinc-300 select-all line-clamp-2">
                            {clip.video_title_for_youtube_short}
                        </p>
                     </div>

                     {/* Caption Field */}
                     <div className="bg-black/20 rounded-lg p-3 border border-white/5 hover:border-white/10 transition-colors">
                        <div className="flex items-center gap-2 text-[10px] font-bold text-zinc-400 mb-1.5 uppercase tracking-wider">
                            <Instagram size={12} className="text-pink-400" /> Caption
                        </div>
                        <p className="text-xs text-zinc-300 select-all line-clamp-2">
                            {clip.video_description_for_instagram || clip.video_description_for_tiktok}
                        </p>
                     </div>
                </div>

                {/* Error Box */}
                {editError && (
                    <div className="p-2 bg-red-500/10 border border-red-500/20 text-red-400 text-[10px] rounded-lg flex items-center gap-2">
                        <AlertCircle size={12} className="shrink-0" /> {editError}
                    </div>
                )}

                {/* Action Buttons (2x2 Grid) */}
                <div className="grid grid-cols-2 gap-2 mt-auto pt-2">
                    <button
                        onClick={handleAutoEdit}
                        disabled={isEditing}
                        className="py-2.5 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white rounded-lg text-xs font-bold transition-all flex items-center justify-center gap-2 disabled:opacity-50"
                    >
                        {isEditing ? <Loader2 size={14} className="animate-spin" /> : <Wand2 size={14} />} 
                        Auto Edit
                    </button>

                    <button
                        onClick={() => setShowSubtitleModal(true)}
                        disabled={isSubtitling}
                        className="py-2.5 bg-gradient-to-r from-yellow-600 to-orange-600 hover:from-yellow-500 hover:to-orange-500 text-white rounded-lg text-xs font-bold transition-all flex items-center justify-center gap-2 disabled:opacity-50"
                    >
                        {isSubtitling ? <Loader2 size={14} className="animate-spin" /> : <Type size={14} />} 
                        Subtitles
                    </button>

                    <button
                        onClick={() => setShowModal(true)}
                        className="py-2.5 bg-primary hover:bg-blue-600 text-white rounded-lg text-xs font-bold transition-all flex items-center justify-center gap-2"
                    >
                        <Share2 size={14} /> Post
                    </button>
                    
                    <button
                        onClick={async (e) => {
                            e.preventDefault();
                            try {
                                const response = await fetch(currentVideoUrl);
                                const blob = await response.blob();
                                const url = window.URL.createObjectURL(blob);
                                const a = document.createElement('a');
                                a.href = url;
                                a.download = `clip-${index + 1}.mp4`;
                                document.body.appendChild(a);
                                a.click();
                                window.URL.revokeObjectURL(url);
                                document.body.removeChild(a);
                            } catch (err) {
                                window.open(currentVideoUrl, '_blank');
                            }
                        }}
                        className="py-2.5 bg-white/5 hover:bg-white/10 text-zinc-300 hover:text-white rounded-lg text-xs font-bold transition-colors flex items-center justify-center gap-2 border border-white/5"
                    >
                        <Download size={14} /> Download
                    </button>
                </div>
            </div>

            {/* Post Modal */}
            {showModal && (
                <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-[fadeIn_0.2s_ease-out]">
                    <div className="bg-[#121214] border border-white/10 p-6 rounded-2xl w-full max-w-md shadow-2xl relative max-h-[90vh] overflow-y-auto custom-scrollbar">
                        <button
                            onClick={() => setShowModal(false)}
                            className="absolute top-4 right-4 text-zinc-500 hover:text-white"
                        >
                            <X size={20} />
                        </button>

                        <h3 className="text-lg font-bold text-white mb-4">Post / Schedule</h3>

                        {!uploadPostKey && (
                            <div className="mb-4 p-3 bg-yellow-500/10 border border-yellow-500/20 text-yellow-200 text-xs rounded-lg flex items-start gap-2">
                                <AlertCircle size={14} className="mt-0.5 shrink-0" />
                                <div>Configure API Key in Settings first.</div>
                            </div>
                        )}

                        <div className="space-y-4 mb-6">
                            <div>
                                <label className="block text-xs font-bold text-zinc-400 mb-1">Video Title</label>
                                <input 
                                    type="text" 
                                    value={postTitle}
                                    onChange={(e) => setPostTitle(e.target.value)}
                                    className="w-full bg-black/40 border border-white/10 rounded-lg p-2 text-sm text-white focus:outline-none focus:border-primary/50 placeholder-zinc-600"
                                    placeholder="Enter a catchy title..."
                                />
                            </div>

                            <div>
                                <label className="block text-xs font-bold text-zinc-400 mb-1">Caption / Description</label>
                                <textarea 
                                    value={postDescription}
                                    onChange={(e) => setPostDescription(e.target.value)}
                                    rows={4}
                                    className="w-full bg-black/40 border border-white/10 rounded-lg p-2 text-sm text-white focus:outline-none focus:border-primary/50 placeholder-zinc-600 resize-none"
                                    placeholder="Write a caption for your post..."
                                />
                            </div>

                            <div className="p-3 bg-white/5 rounded-lg border border-white/5">
                                <div className="flex items-center justify-between mb-2">
                                    <div className="flex items-center gap-2 text-sm text-white font-medium">
                                        <Calendar size={16} className="text-purple-400" /> Schedule Post
                                    </div>
                                    <label className="relative inline-flex items-center cursor-pointer">
                                        <input type="checkbox" checked={isScheduling} onChange={(e) => setIsScheduling(e.target.checked)} className="sr-only peer" />
                                        <div className="w-9 h-5 bg-zinc-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-purple-600"></div>
                                    </label>
                                </div>
                                
                                {isScheduling && (
                                    <div className="mt-3 animate-[fadeIn_0.2s_ease-out]">
                                        <label className="block text-xs text-zinc-400 mb-1">Select Date & Time</label>
                                        <div className="relative">
                                            <input 
                                                type="datetime-local" 
                                                value={scheduleDate}
                                                onChange={(e) => setScheduleDate(e.target.value)}
                                                className="w-full bg-black/40 border border-white/10 rounded-lg p-2 pl-9 text-sm text-white focus:outline-none focus:border-purple-500/50 [color-scheme:dark]"
                                            />
                                            <Clock size={14} className="absolute left-3 top-2.5 text-zinc-500" />
                                        </div>
                                    </div>
                                )}
                            </div>

                            <div>
                                <label className="block text-xs font-bold text-zinc-400 mb-2">Select Platforms</label>
                                <div className="grid grid-cols-1 gap-2">
                                    <label className="flex items-center gap-3 p-3 bg-white/5 rounded-lg cursor-pointer hover:bg-white/10 transition-colors border border-white/5">
                                        <input type="checkbox" checked={platforms.tiktok} onChange={e => setPlatforms({ ...platforms, tiktok: e.target.checked })} className="w-4 h-4 rounded border-zinc-600 bg-black/50 text-primary focus:ring-primary" />
                                        <div className="flex items-center gap-2 text-sm text-white"><Video size={16} className="text-cyan-400" /> TikTok</div>
                                    </label>
                                    <label className="flex items-center gap-3 p-3 bg-white/5 rounded-lg cursor-pointer hover:bg-white/10 transition-colors border border-white/5">
                                        <input type="checkbox" checked={platforms.instagram} onChange={e => setPlatforms({ ...platforms, instagram: e.target.checked })} className="w-4 h-4 rounded border-zinc-600 bg-black/50 text-primary focus:ring-primary" />
                                        <div className="flex items-center gap-2 text-sm text-white"><Instagram size={16} className="text-pink-400" /> Instagram</div>
                                    </label>
                                    <label className="flex items-center gap-3 p-3 bg-white/5 rounded-lg cursor-pointer hover:bg-white/10 transition-colors border border-white/5">
                                        <input type="checkbox" checked={platforms.youtube} onChange={e => setPlatforms({ ...platforms, youtube: e.target.checked })} className="w-4 h-4 rounded border-zinc-600 bg-black/50 text-primary focus:ring-primary" />
                                        <div className="flex items-center gap-2 text-sm text-white"><Youtube size={16} className="text-red-400" /> YouTube Shorts</div>
                                    </label>
                                </div>
                            </div>
                        </div>

                        {postResult && (
                            <div className={`mb-4 p-3 rounded-lg text-xs flex items-start gap-2 ${postResult.success ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400'}`}>
                                {postResult.success ? <CheckCircle size={14} className="mt-0.5 shrink-0" /> : <AlertCircle size={14} className="mt-0.5 shrink-0" />}
                                <div>{postResult.msg}</div>
                            </div>
                        )}

                        <button
                            onClick={handlePost}
                            disabled={posting || !uploadPostKey}
                            className="w-full py-3 bg-primary hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed rounded-xl text-white font-bold transition-all flex items-center justify-center gap-2"
                        >
                            {posting ? <><Loader2 size={16} className="animate-spin" /> {isScheduling ? 'Scheduling...' : 'Publishing...'}</> : <><Share2 size={16} /> {isScheduling ? 'Schedule Post' : 'Publish Now'}</>}
                        </button>
                    </div>
                </div>
            )}

            <SubtitleModal 
                isOpen={showSubtitleModal}
                onClose={() => setShowSubtitleModal(false)}
                onGenerate={handleSubtitle}
                isProcessing={isSubtitling}
                videoUrl={currentVideoUrl}
            />
        </div>
    );
}
