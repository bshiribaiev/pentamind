import { useState, useEffect, useRef, useCallback } from 'react';
import { Zap, X, Mic, MicOff, Upload, FileText, ChevronDown, ChevronUp, Maximize2, Minimize2 } from 'lucide-react';
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
  const [isListening, setIsListening] = useState(false);
  const [uploadedFile, setUploadedFile] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  
  const fileInputRef = useRef<HTMLInputElement>(null);
  const recognitionRef = useRef<any>(null);

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
    
    // Initialize window - start with ignore cursor events enabled for click-through
    // The mouse enter/leave handlers will toggle this
    const initWindow = async () => {
      try {
        const appWindow = getCurrentWindow();
        // Start with click-through enabled - mouse enter will disable it for interaction
        await appWindow.setIgnoreCursorEvents(true, { forward: true });
      } catch (e) {
        // Not available on all platforms
      }
    };
    initWindow();
  }, [resizeWindow]);

  // Click-through for transparent areas on macOS
  // When mouse enters the app, allow interaction; when it leaves, allow clicks to pass through
  const handleMouseEnter = useCallback(async () => {
    try {
      const appWindow = getCurrentWindow();
      await appWindow.setIgnoreCursorEvents(false);
    } catch (e) {
      // Not available on all platforms
    }
  }, []);

  const handleMouseLeave = useCallback(async () => {
    try {
      const appWindow = getCurrentWindow();
      // Re-enable click-through when mouse leaves the visible content
      await appWindow.setIgnoreCursorEvents(true, { forward: true });
    } catch (e) {
      // Not available on all platforms
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

  // Voice input (may not work in all WebViews)
  const toggleVoiceInput = useCallback(() => {
    try {
      const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
      
      if (!SpeechRecognition) {
        setError('Voice input not available. Use text input instead.');
        return;
      }

      if (isListening) {
        recognitionRef.current?.stop();
        setIsListening(false);
        return;
      }

      const recognition = new SpeechRecognition();
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.lang = 'en-US';

      recognition.onresult = (event: any) => {
        let transcript = '';
        for (let i = 0; i < event.results.length; i++) {
          transcript += event.results[i][0].transcript;
        }
        setInputText(transcript);
      };

      recognition.onerror = (e: any) => {
        console.error('Speech error:', e);
        setIsListening(false);
        setError('Voice input error. Try again.');
      };
      
      recognition.onend = () => setIsListening(false);

      recognitionRef.current = recognition;
      recognition.start();
      setIsListening(true);
    } catch (e) {
      setError('Voice input not supported in this app.');
    }
  }, [isListening]);

  // File handling
  const handleFile = useCallback(async (file: File) => {
    const ext = file.name.split('.').pop()?.toLowerCase();
    if (!['txt', 'md', 'json', 'csv'].includes(ext || '')) {
      setError('Supported: txt, md, json, csv');
      return;
    }
    try {
      const text = await file.text();
      setInputText(text);
      setUploadedFile(file.name);
    } catch {
      setError('Failed to read file');
    }
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files[0]) handleFile(e.dataTransfer.files[0]);
  }, [handleFile]);

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
      
      // Auto-expand when response is ready in overlay mode
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

  return (
    <div 
      className="h-screen flex flex-col bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 text-white overflow-hidden rounded-xl"
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      {/* Header */}
      <div 
        data-tauri-drag-region
        className="flex items-center justify-between px-4 py-3 border-b border-slate-800 bg-slate-900/80 cursor-grab active:cursor-grabbing"
      >
        <div data-tauri-drag-region className="flex items-center gap-2 pointer-events-none">
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
            onClick={closeApp}
            className="p-1.5 hover:bg-slate-800 rounded text-slate-400 hover:text-white transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden p-4 gap-3">
        {/* Input Section */}
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium text-slate-400">Input</span>
          <div className="flex gap-1">
            <button
              onClick={() => fileInputRef.current?.click()}
              className="p-1.5 hover:bg-slate-800 rounded text-slate-400 hover:text-white"
              title="Upload file"
            >
              <Upload className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={toggleVoiceInput}
              className={`p-1.5 rounded transition-colors ${
                isListening ? 'bg-red-600 text-white' : 'hover:bg-slate-800 text-slate-400 hover:text-white'
              }`}
              title={isListening ? 'Stop' : 'Voice input'}
            >
              {isListening ? <MicOff className="w-3.5 h-3.5" /> : <Mic className="w-3.5 h-3.5" />}
            </button>
          </div>
        </div>

        <input
          ref={fileInputRef}
          type="file"
          accept=".txt,.md,.json,.csv"
          onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
          className="hidden"
        />

        {uploadedFile && (
          <div className="flex items-center gap-2 px-2 py-1.5 bg-slate-800 rounded text-xs">
            <FileText className="w-3 h-3 text-blue-400" />
            <span className="text-slate-300 truncate flex-1">{uploadedFile}</span>
            <button onClick={() => { setUploadedFile(null); setInputText(''); }} className="text-slate-500 hover:text-white">
              <X className="w-3 h-3" />
            </button>
          </div>
        )}

        <div
          onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={handleDrop}
          className={`relative ${isOverlayMode && !isExpanded ? 'h-20' : 'h-32'} transition-all`}
        >
          <textarea
            value={inputText}
            onChange={(e) => { setInputText(e.target.value); setUploadedFile(null); }}
            placeholder="Type, paste, drag file, or use voice..."
            className={`w-full h-full bg-slate-900 border rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-blue-500 resize-none ${
              isDragging ? 'border-blue-500' : 'border-slate-700'
            }`}
          />
          {isDragging && (
            <div className="absolute inset-0 bg-blue-600/20 border-2 border-dashed border-blue-500 rounded-lg flex items-center justify-center">
              <span className="text-blue-400 text-sm">Drop file</span>
            </div>
          )}
        </div>

        {/* Task Buttons */}
        <div className="flex gap-1.5 flex-wrap">
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
          className={`w-full py-2.5 rounded-lg font-medium text-sm flex items-center justify-center gap-2 transition-all ${
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

        {error && (
          <div className="px-3 py-2 bg-red-900/50 border border-red-700 rounded text-red-200 text-xs">
            {error}
          </div>
        )}

        {/* Response Section - Only shown when expanded or in full mode */}
        {response && (isExpanded || !isOverlayMode) && (
          <div className="flex-1 overflow-auto mt-2 border-t border-slate-800 pt-3">
            <div className="mb-3">
              {renderMarkdown(response.final)}
            </div>
            
            <div className="flex items-center gap-2 text-xs text-slate-500 pt-2 border-t border-slate-800">
              <span>by</span>
              <span className="px-2 py-0.5 bg-slate-800 text-slate-300 rounded font-mono text-xs">
                {response.winner_model}
              </span>
              <span className="text-slate-600">•</span>
              <span>{response.trace.reduce((a, b) => a + b.latency_ms, 0)}ms</span>
            </div>
          </div>
        )}

        {/* Expand/Collapse button for overlay mode */}
        {isOverlayMode && response && (
          <button
            onClick={toggleExpanded}
            className="flex items-center justify-center gap-1 py-1.5 text-xs text-slate-400 hover:text-white transition-colors"
          >
            {isExpanded ? (
              <>
                <ChevronUp className="w-3 h-3" />
                Collapse
              </>
            ) : (
              <>
                <ChevronDown className="w-3 h-3" />
                Show Response
              </>
            )}
          </button>
        )}
      </div>
    </div>
  );
}

export default App;
export type { TaskType, TraceStep, JuryResponse };
