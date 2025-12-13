import { useState, useEffect, useRef, useCallback } from 'react';
import { Zap, X, Upload, FileText, ChevronDown, ChevronUp, Maximize2, Minimize2, Loader2, Mic, MicOff, RotateCcw, Minus } from 'lucide-react';
import { getCurrentWindow } from '@tauri-apps/api/window';

export interface TaskType {
  id: 'summarize' | 'research' | 'solve' | 'code' | 'rewrite';
  name: string;
}

export interface TraceStep {
  step: string;
  model?: string;
  latency_ms: number;
  data?: any;
  status?: 'pending' | 'active' | 'complete' | 'error';
}

export interface JuryResponse {
  final: string;
  winner_model: string;
  task_spec: {
    intent: string;
    format: string;
    needs_citations: boolean;
    confidence: number;
  };
  scoreboard: any[];
  trace: TraceStep[];
}

const TASK_TYPES: TaskType[] = [
  { id: 'summarize', name: 'Summarize' },
  { id: 'research', name: 'Research' },
  { id: 'solve', name: 'Solve' },
  { id: 'code', name: 'Code' },
  { id: 'rewrite', name: 'Rewrite' },
];

// Simple markdown renderer
function renderMarkdown(text: string) {
  const lines = text.split('\n');
  const elements: JSX.Element[] = [];
  let listItems: string[] = [];

  const processInline = (line: string) => {
    let processed = line.replace(/\*\*([^*]+)\*\*/g, '<strong class="font-semibold text-white">$1</strong>');
    processed = processed.replace(/`([^`]+)`/g, '<code class="px-1 py-0.5 bg-slate-700 rounded text-blue-300 text-xs">$1</code>');
    return processed;
  };

  const flushList = () => {
    if (listItems.length > 0) {
      elements.push(
        <ul key={elements.length} className="list-disc list-inside space-y-1 my-2 ml-2">
          {listItems.map((item, i) => (
            <li key={i} className="text-slate-200 text-sm" dangerouslySetInnerHTML={{ __html: processInline(item) }} />
          ))}
        </ul>
      );
      listItems = [];
    }
  };

  lines.forEach((line, i) => {
    if (line.startsWith('### ')) {
      flushList();
      elements.push(<h3 key={i} className="text-base font-bold text-white mt-3 mb-1">{line.slice(4)}</h3>);
    } else if (line.startsWith('## ')) {
      flushList();
      elements.push(<h2 key={i} className="text-lg font-bold text-white mt-3 mb-1">{line.slice(3)}</h2>);
    } else if (/^\d+\.\s/.test(line) || line.startsWith('- ') || line.startsWith('* ')) {
      const content = line.replace(/^(\d+\.\s|-\s|\*\s)/, '');
      listItems.push(content);
    } else if (line === '---') {
      flushList();
      elements.push(<hr key={i} className="border-slate-700 my-3" />);
    } else if (line.trim() === '') {
      flushList();
    } else {
      flushList();
      elements.push(
        <p key={i} className="text-slate-200 text-sm leading-relaxed" dangerouslySetInnerHTML={{ __html: processInline(line) }} />
      );
    }
  });

  flushList();
  return elements;
}

function App() {
  // App state
  const [inputText, setInputText] = useState('');
  const [selectedTask, setSelectedTask] = useState<string>('research');
  const [isProcessing, setIsProcessing] = useState(false);
  const [response, setResponse] = useState<JuryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  
  // UI state
  const [isExpanded, setIsExpanded] = useState(false);
  const [isOverlayMode, setIsOverlayMode] = useState(true);
  const [uploadedFile, setUploadedFile] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isParsingFile, setIsParsingFile] = useState(false);
  
  // Voice state
  const [isRecording, setIsRecording] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Window sizing
  const resizeWindow = useCallback(async (expanded: boolean, overlayMode: boolean) => {
    try {
      const appWindow = getCurrentWindow();
      if (overlayMode) {
        if (expanded) {
          await appWindow.setSize({ type: 'Logical', width: 800, height: 600 });
        } else {
          await appWindow.setSize({ type: 'Logical', width: 420, height: 380 });
        }
        await appWindow.setAlwaysOnTop(true);
      } else {
        await appWindow.setSize({ type: 'Logical', width: 1200, height: 800 });
        await appWindow.setAlwaysOnTop(false);
      }
      await appWindow.center();
    } catch (e) {
      console.log('Window resize not available');
    }
  }, []);

  // Initial setup
  useEffect(() => {
    resizeWindow(false, true);
  }, [resizeWindow]);

  // Global keyboard shortcut to show/focus the window (Cmd/Ctrl+Shift+P)
  useEffect(() => {
    const handleGlobalKey = async (e: KeyboardEvent) => {
      // Cmd+Shift+P (Mac) or Ctrl+Shift+P (Windows/Linux) to toggle visibility
      if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key.toLowerCase() === 'p') {
        e.preventDefault();
        try {
          const appWindow = getCurrentWindow();
          await appWindow.show();
          await appWindow.setFocus();
        } catch {
          // Ignore
        }
      }
    };
    
    window.addEventListener('keydown', handleGlobalKey);
    return () => window.removeEventListener('keydown', handleGlobalKey);
  }, []);

  // Direct drag handler - more reliable than data-tauri-drag-region
  const handleWindowDrag = useCallback(async (e: React.MouseEvent) => {
    if ((e.target as HTMLElement).closest('button')) return;
    try {
      const appWindow = getCurrentWindow();
      await appWindow.startDragging();
    } catch (err) {
      console.log('Drag not available');
    }
  }, []);

  // Toggle expanded view
  const toggleExpanded = useCallback(() => {
    const newExpanded = !isExpanded;
    setIsExpanded(newExpanded);
    resizeWindow(newExpanded, isOverlayMode);
  }, [isExpanded, isOverlayMode, resizeWindow]);

  // Toggle between overlay and full mode
  const toggleMode = useCallback(() => {
    const newMode = !isOverlayMode;
    setIsOverlayMode(newMode);
    if (!newMode) {
      setIsExpanded(true);
    }
    resizeWindow(newMode ? isExpanded : true, newMode);
  }, [isOverlayMode, isExpanded, resizeWindow]);

  // Voice recording
  const startRecording = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          audioChunksRef.current.push(e.data);
        }
      };

      mediaRecorder.onstop = async () => {
        stream.getTracks().forEach(track => track.stop());
        
        if (audioChunksRef.current.length > 0) {
          setIsTranscribing(true);
          try {
            const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
            
            // Send to backend for transcription
            const formData = new FormData();
            formData.append('audio', audioBlob, 'recording.webm');
            
            const result = await fetch('http://localhost:8000/transcribe', {
              method: 'POST',
              body: formData,
            });
            
            if (result.ok) {
              const data = await result.json();
              if (data.text) {
                setInputText(prev => prev ? `${prev} ${data.text}` : data.text);
              }
            } else {
              // Fallback: show error but don't break
              console.log('Transcription not available');
              setError('Voice transcription not available. Type your input instead.');
            }
          } catch (err) {
            console.error('Transcription error:', err);
            setError('Voice transcription failed. Backend may not support it yet.');
          } finally {
            setIsTranscribing(false);
          }
        }
      };

      mediaRecorder.start(100);
      setIsRecording(true);
      setError(null);
    } catch (err) {
      console.error('Microphone error:', err);
      setError('Could not access microphone. Check permissions.');
    }
  }, []);

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  }, [isRecording]);

  const toggleRecording = useCallback(() => {
    if (isRecording) {
      stopRecording();
    } else {
      startRecording();
    }
  }, [isRecording, startRecording, stopRecording]);

  // File handling - simple text extraction, PDFs sent to backend
  const handleFile = useCallback(async (file: File) => {
    console.log('handleFile called:', file.name, file.type, file.size);
    
    const ext = file.name.split('.').pop()?.toLowerCase() || '';
    const supportedText = ['txt', 'md', 'json', 'csv'];
    const supportedDocs = ['pdf', 'doc', 'docx'];
    
    console.log('File extension:', ext);
    
    if (!supportedText.includes(ext) && !supportedDocs.includes(ext)) {
      setError(`Unsupported format: .${ext}. Use: txt, md, json, csv, pdf, docx`);
      return;
    }
    
    setIsParsingFile(true);
    setError(null);
    
    try {
      if (supportedText.includes(ext)) {
        // Plain text files - read directly
        console.log('Reading as text file');
        const text = await file.text();
        setInputText(text);
        setUploadedFile(file.name);
        console.log('Text file loaded:', text.length, 'chars');
      } else {
        // PDF/DOC/DOCX - send to backend for parsing
        console.log('Sending to backend for parsing');
        const formData = new FormData();
        formData.append('file', file);
        
        try {
          const result = await fetch('http://localhost:8000/parse_document', {
            method: 'POST',
            body: formData,
          });
          
          console.log('Backend response status:', result.status);
          
          if (result.ok) {
            const data = await result.json();
            console.log('Parsed document:', data.text?.length, 'chars');
            if (data.text) {
              setInputText(data.text);
              setUploadedFile(file.name);
            } else {
              setError('Document appears to be empty.');
            }
          } else {
            const errorText = await result.text();
            console.log('Backend error:', errorText);
            // Fallback: try to extract text from docx locally
            if (ext === 'docx') {
              console.log('Attempting local DOCX extraction');
              const arrayBuffer = await file.arrayBuffer();
              const text = new TextDecoder('utf-8', { fatal: false }).decode(new Uint8Array(arrayBuffer));
              const matches = text.match(/<w:t[^>]*>([^<]+)<\/w:t>/g);
              if (matches && matches.length > 0) {
                const extractedText = matches.map(m => m.replace(/<[^>]+>/g, '')).join(' ');
                setInputText(extractedText);
                setUploadedFile(file.name);
                console.log('Local DOCX extraction successful:', extractedText.length, 'chars');
              } else {
                setError('Could not parse DOCX. Try converting to PDF.');
              }
            } else {
              setError(`Backend error: ${result.status}. Start the server for PDF support.`);
            }
          }
        } catch (fetchError) {
          console.log('Fetch error (backend probably not running):', fetchError);
          // Backend not available - try local extraction for docx
          if (ext === 'docx') {
            console.log('Backend unavailable, attempting local DOCX extraction');
            const arrayBuffer = await file.arrayBuffer();
            const text = new TextDecoder('utf-8', { fatal: false }).decode(new Uint8Array(arrayBuffer));
            const matches = text.match(/<w:t[^>]*>([^<]+)<\/w:t>/g);
            if (matches && matches.length > 0) {
              const extractedText = matches.map(m => m.replace(/<[^>]+>/g, '')).join(' ');
              setInputText(extractedText);
              setUploadedFile(file.name);
              console.log('Local extraction successful');
            } else {
              setError('Could not parse DOCX locally. Start the backend server.');
            }
          } else {
            setError('Backend not running. Start with: cd backend && ./start.sh');
          }
        }
      }
    } catch (err) {
      console.error('File parsing error:', err);
      setError(`Failed to read file: ${err}`);
    } finally {
      setIsParsingFile(false);
    }
  }, []);

  // Drag and drop handlers - handle at document level for better reliability
  const handleDragOver = useCallback((e: React.DragEvent | DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!isDragging) setIsDragging(true);
  }, [isDragging]);

  const handleDragLeave = useCallback((e: React.DragEvent | DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    // Only set to false if leaving the window entirely
    const relatedTarget = (e as any).relatedTarget;
    if (!relatedTarget || !(e.currentTarget as HTMLElement)?.contains(relatedTarget)) {
      setIsDragging(false);
    }
  }, []);

  const handleDrop = useCallback((e: React.DragEvent | DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    
    const files = (e as DragEvent).dataTransfer?.files || (e as React.DragEvent).dataTransfer?.files;
    console.log('Drop event - files:', files?.length, files?.[0]?.name);
    
    if (files && files.length > 0) {
      const file = files[0];
      console.log('Processing file:', file.name, file.type, file.size);
      handleFile(file);
    }
  }, [handleFile]);

  // Set up document-level drag listeners for better reliability
  useEffect(() => {
    const handleDocDragOver = (e: DragEvent) => {
      e.preventDefault();
      if (!isDragging) setIsDragging(true);
    };
    
    const handleDocDragLeave = (e: DragEvent) => {
      e.preventDefault();
      // Check if we're leaving the window
      if (e.clientX <= 0 || e.clientY <= 0 || 
          e.clientX >= window.innerWidth || e.clientY >= window.innerHeight) {
        setIsDragging(false);
      }
    };
    
    const handleDocDrop = (e: DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      
      const files = e.dataTransfer?.files;
      if (files && files.length > 0) {
        handleFile(files[0]);
      }
    };
    
    document.addEventListener('dragover', handleDocDragOver);
    document.addEventListener('dragleave', handleDocDragLeave);
    document.addEventListener('drop', handleDocDrop);
    
    return () => {
      document.removeEventListener('dragover', handleDocDragOver);
      document.removeEventListener('dragleave', handleDocDragLeave);
      document.removeEventListener('drop', handleDocDrop);
    };
  }, [handleFile, isDragging]);

  // Submit
  const handleSubmit = async () => {
    if (!inputText.trim() || isProcessing) return;

    setIsProcessing(true);
    setError(null);

    try {
      const result = await fetch('http://localhost:8000/run_jury', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task: selectedTask, input: inputText }),
      });

      if (!result.ok) throw new Error(`API error: ${result.statusText}`);

      const data: JuryResponse = await result.json();
      setResponse(data);
      
      if (isOverlayMode && !isExpanded) {
        setIsExpanded(true);
        resizeWindow(true, true);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setIsProcessing(false);
    }
  };

  const closeApp = async () => {
    try {
      const appWindow = getCurrentWindow();
      await appWindow.close();
    } catch {
      // Fallback
    }
  };

  const hideApp = async () => {
    try {
      const appWindow = getCurrentWindow();
      await appWindow.hide();
    } catch {
      // Fallback - try minimize instead
      try {
        const appWindow = getCurrentWindow();
        await appWindow.minimize();
      } catch {
        // Ignore
      }
    }
  };

  // Start a new query - clear response and resize window back to compact
  const startNewQuery = useCallback(() => {
    setResponse(null);
    setIsExpanded(false);
    setInputText('');
    setUploadedFile(null);
    setError(null);
    // Resize back to compact overlay size
    if (isOverlayMode) {
      resizeWindow(false, true);
    }
  }, [isOverlayMode, resizeWindow]);

  return (
    <div className="h-screen flex flex-col bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 text-white overflow-hidden rounded-xl relative">
      {/* Global Drop Overlay - Shows when dragging files anywhere */}
      {isDragging && (
        <div className="absolute inset-0 z-50 bg-slate-900/95 flex items-center justify-center pointer-events-none">
          <div className="text-center p-8 border-2 border-dashed border-blue-500 rounded-2xl bg-blue-900/20">
            <Upload className="w-12 h-12 text-blue-400 mx-auto mb-3" />
            <p className="text-blue-400 text-lg font-medium">Drop your file here</p>
            <p className="text-blue-400/60 text-sm mt-2">PDF, DOCX, TXT, MD, JSON, CSV</p>
          </div>
        </div>
      )}
      
      {/* Header - Drag Handle */}
      <div 
        onMouseDown={handleWindowDrag}
        className="flex items-center justify-between px-4 py-3 border-b border-slate-800 bg-slate-900/80 cursor-grab active:cursor-grabbing select-none"
      >
        <div className="flex items-center gap-2 pointer-events-none">
          <div className="w-8 h-8 bg-gradient-to-br from-blue-600 to-indigo-600 rounded-lg flex items-center justify-center">
            <Zap className="w-4 h-4 text-white" />
          </div>
          <span className="font-semibold text-sm">Pentamind</span>
        </div>
        
        <div className="flex items-center gap-1">
          <button
            onClick={toggleMode}
            className="p-1.5 hover:bg-slate-800 rounded text-slate-400 hover:text-white transition-colors"
            title={isOverlayMode ? 'Switch to full mode' : 'Switch to overlay mode'}
          >
            {isOverlayMode ? <Maximize2 className="w-4 h-4" /> : <Minimize2 className="w-4 h-4" />}
          </button>
          <button
            onClick={hideApp}
            className="p-1.5 hover:bg-slate-800 rounded text-slate-400 hover:text-yellow-400 transition-colors"
            title="Hide window (click dock icon to show again)"
          >
            <Minus className="w-4 h-4" />
          </button>
          <button
            onClick={closeApp}
            className="p-1.5 hover:bg-slate-800 rounded text-slate-400 hover:text-red-400 transition-colors"
            title="Close app"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden p-4">
        {/* Determine if we're in "response mode" - showing a response */}
        {(() => {
          const showingResponse = response && (isExpanded || !isOverlayMode);
          
          return (
            <>
              {/* Input Section - Collapsible when showing response */}
              {!showingResponse && (
                <>
                  {/* Input Section Header */}
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-medium text-slate-400">Input</span>
                    <div className="flex items-center gap-1">
                      {/* Voice Button */}
                      <button
                        onClick={toggleRecording}
                        disabled={isTranscribing}
                        className={`p-1.5 rounded transition-colors ${
                          isRecording 
                            ? 'bg-red-600 text-white animate-pulse' 
                            : isTranscribing
                              ? 'bg-slate-700 text-slate-400'
                              : 'hover:bg-slate-800 text-slate-400 hover:text-white'
                        }`}
                        title={isRecording ? 'Stop recording' : isTranscribing ? 'Transcribing...' : 'Voice input'}
                      >
                        {isTranscribing ? (
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        ) : isRecording ? (
                          <MicOff className="w-3.5 h-3.5" />
                        ) : (
                          <Mic className="w-3.5 h-3.5" />
                        )}
                      </button>
                      
                      {/* Upload Button */}
                      <button
                        onClick={() => fileInputRef.current?.click()}
                        className="p-1.5 hover:bg-slate-800 rounded text-slate-400 hover:text-white"
                        title="Upload file (PDF, DOC, TXT)"
                        disabled={isParsingFile}
                      >
                        {isParsingFile ? (
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        ) : (
                          <Upload className="w-3.5 h-3.5" />
                        )}
                      </button>
                    </div>
                  </div>

                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".txt,.md,.json,.csv,.pdf,.doc,.docx,text/*,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
                    className="hidden"
                  />

                  {uploadedFile && (
                    <div className="flex items-center gap-2 px-2 py-1.5 bg-slate-800 rounded text-xs mb-2">
                      <FileText className="w-3 h-3 text-blue-400" />
                      <span className="text-slate-300 truncate flex-1">{uploadedFile}</span>
                      <button onClick={() => { setUploadedFile(null); setInputText(''); }} className="text-slate-500 hover:text-white">
                        <X className="w-3 h-3" />
                      </button>
                    </div>
                  )}

                  {/* Text Input Area - Full size when no response */}
                  <div
                    onDragOver={handleDragOver}
                    onDragLeave={handleDragLeave}
                    onDrop={handleDrop}
                    className="relative flex-1 min-h-[120px] mb-3"
                  >
                    <textarea
                      value={inputText}
                      onChange={(e) => { setInputText(e.target.value); setUploadedFile(null); }}
                      placeholder="Type, paste, or drop a file here..."
                      className={`w-full h-full bg-slate-900 border rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-blue-500 resize-none ${
                        isDragging ? 'border-blue-500 bg-blue-900/20' : 'border-slate-700'
                      }`}
                    />
                    {isDragging && (
                      <div className="absolute inset-0 bg-blue-600/20 border-2 border-dashed border-blue-500 rounded-lg flex items-center justify-center pointer-events-none">
                        <div className="text-center">
                          <Upload className="w-8 h-8 text-blue-400 mx-auto mb-2" />
                          <span className="text-blue-400 text-sm font-medium">Drop file here</span>
                          <p className="text-blue-400/60 text-xs mt-1">PDF, DOC, TXT, MD</p>
                        </div>
                      </div>
                    )}
                  </div>
                </>
              )}

              {/* Compact Input Preview - When showing response */}
              {showingResponse && (
                <div className="mb-3 p-2 bg-slate-800/50 rounded-lg border border-slate-700">
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-slate-400">Query</span>
                    <button
                      onClick={startNewQuery}
                      className="text-xs text-slate-400 hover:text-white flex items-center gap-1 transition-colors"
                    >
                      <RotateCcw className="w-3 h-3" />
                      New Query
                    </button>
                  </div>
                  <p className="text-sm text-slate-300 mt-1 line-clamp-2">{inputText}</p>
                </div>
              )}

              {/* Response Section - Takes most space when visible */}
              {showingResponse && (
                <div className="flex-1 overflow-auto mb-3">
                  <div className="mb-3">
                    {renderMarkdown(response.final)}
                  </div>
                  
                  <div className="flex items-center gap-2 text-xs text-slate-500 pt-3 border-t border-slate-800">
                    <span>by</span>
                    <span className="px-2 py-0.5 bg-slate-800 text-slate-300 rounded font-mono text-xs">
                      {response.winner_model}
                    </span>
                    <span className="text-slate-600">•</span>
                    <span>{response.trace.reduce((a, b) => a + b.latency_ms, 0)}ms</span>
                  </div>
                </div>
              )}

              {/* Expand/Collapse button - Only in overlay mode with collapsed response */}
              {isOverlayMode && response && !isExpanded && (
                <button
                  onClick={toggleExpanded}
                  className="flex items-center justify-center gap-1 py-2 text-xs text-slate-400 hover:text-white transition-colors mb-2 bg-slate-800/50 rounded-lg"
                >
                  <ChevronDown className="w-3 h-3" />
                  Show Response
                </button>
              )}

              {error && (
                <div className="px-3 py-2 bg-red-900/50 border border-red-700 rounded text-red-200 text-xs mb-3">
                  {error}
                </div>
              )}

              {/* Task Buttons & Execute - Only when NOT showing response */}
              {!showingResponse && (
                <>
                  {/* Task Buttons */}
                  <div className="flex gap-1.5 flex-wrap mb-3">
                    {TASK_TYPES.map((task) => (
                      <button
                        key={task.id}
                        onClick={() => setSelectedTask(task.id)}
                        className={`px-3 py-1.5 rounded text-xs font-medium transition-all ${
                          selectedTask === task.id
                            ? 'bg-slate-700 text-white'
                            : 'bg-slate-800/50 text-slate-400 hover:text-white'
                        }`}
                      >
                        {task.name}
                      </button>
                    ))}
                  </div>

                  {/* Execute Button */}
                  <button
                    onClick={handleSubmit}
                    disabled={!inputText.trim() || isProcessing}
                    className={`w-full py-2.5 rounded-lg font-medium text-sm flex items-center justify-center gap-2 transition-all mt-auto ${
                      isProcessing
                        ? 'bg-slate-700 text-slate-400 cursor-not-allowed'
                        : 'bg-gradient-to-r from-blue-600 to-indigo-600 text-white hover:shadow-lg hover:shadow-blue-600/30'
                    }`}
                  >
                    {isProcessing ? (
                      <>
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" />
                        Processing...
                      </>
                    ) : (
                      <>
                        <Zap className="w-4 h-4" />
                        Execute
                      </>
                    )}
                  </button>
                </>
              )}
            </>
          );
        })()}
      </div>
    </div>
  );
}

export default App;
export type { TaskType, TraceStep, JuryResponse };
