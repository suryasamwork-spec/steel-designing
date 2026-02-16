import React, { useState, useRef, useEffect } from 'react';
import { Stage, Layer, Image as KonvaImage, Rect, Line, Text, Group } from 'react-konva';
import { Upload, Ruler, Target, Trash2, ChevronLeft, ChevronRight, FileText, Calculator, RotateCcw } from 'lucide-react';
import { renderPage, extractText } from './api';

const App = () => {
    const [file, setFile] = useState(null);
    const [pageImage, setPageImage] = useState(null);
    const [pageNum, setPageNum] = useState(0);
    const [zoom, setZoom] = useState(2.0);
    const [mode, setMode] = useState('select'); // 'select', 'calibrate', 'measure'
    const [scale, setScale] = useState(1.0);

    // Selection state
    const [selections, setSelections] = useState([]);
    const [newSelection, setNewSelection] = useState(null);
    const [isDragging, setIsDragging] = useState(false);

    // Calibration state
    const [calibrationPoints, setCalibrationPoints] = useState([]);
    const [pixelsPerUnit, setPixelsPerUnit] = useState(null);
    const [unitLabel, setUnitLabel] = useState('ft');

    // OCR Results
    const [results, setResults] = useState({ elevations: [], total: 0, studsLabelCount: 0, profiles: {} });
    const [loading, setLoading] = useState(false);
    const loadingRef = useRef(false);

    const setAppLoading = (val) => {
        setLoading(val);
        loadingRef.current = val;
    };

    const fileInputRef = useRef(null);
    const imageRef = useRef(null);

    const handleFileUpload = async (e) => {
        const uploadedFile = e.target.files[0];
        if (uploadedFile) {
            setFile(uploadedFile);
            setPageNum(0);
            loadPage(uploadedFile, 0);
        }
    };

    const [loadingStatus, setLoadingStatus] = useState("");

    const loadPage = async (pdfFile, pNum) => {
        setAppLoading(true);
        setLoadingStatus("Fetching PDF from server...");
        console.log(`📡 loadPage starting: Page ${pNum}`);
        try {
            const imageUrl = await renderPage(pdfFile, pNum, zoom);
            console.log("✅ API response received, creating image object...");
            setLoadingStatus("Rendering drawing...");

            const img = new Image();
            img.src = imageUrl;

            const loadTimeout = setTimeout(() => {
                if (loadingRef.current) {
                    console.log("⏰ Loading timeout reached");
                    alert("Timeout: The drawing is taking too long to display. Try reducing zoom or checking the file size.");
                    setAppLoading(false);
                    setLoadingStatus("");
                }
            }, 20000); // Increased to 20s

            img.onload = () => {
                console.log(`🎨 Image loaded successfully: ${img.width}x${img.height}`);
                clearTimeout(loadTimeout);
                setPageImage(img);
                setAppLoading(false);
                setLoadingStatus("");
            };
            img.onerror = (e) => {
                console.log("❌ Image object error:", e);
                clearTimeout(loadTimeout);
                alert("The server sent the data, but the browser couldn't display it as an image.");
                setAppLoading(false);
                setLoadingStatus("");
            };
        } catch (err) {
            console.error("❌ API failure in loadPage:", err);
            alert("Connection error: Could not reach the backend server on port 5001.");
            setAppLoading(false);
            setLoadingStatus("");
        }
    };

    const handleZoomIn = () => {
        setScale(prev => Math.min(prev + 0.25, 3.0)); // Max 300%
    };

    const handleZoomOut = () => {
        setScale(prev => Math.max(prev - 0.25, 0.25)); // Min 25%
    };

    const handleResetZoom = () => {
        setScale(1.0);
    };

    const handleMouseDown = (e) => {
        if (mode === 'select') {
            const pos = e.target.getStage().getRelativePointerPosition();
            setNewSelection({ startX: pos.x, startY: pos.y, currentX: pos.x, currentY: pos.y });
            setIsDragging(true);
        } else if (mode === 'calibrate' && calibrationPoints.length < 2) {
            const pos = e.target.getStage().getRelativePointerPosition();
            setCalibrationPoints([...calibrationPoints, pos]);
        }
    };

    const handleMouseMove = (e) => {
        if (!newSelection || !isDragging || mode !== 'select') return;
        const stage = e.target.getStage();
        const pos = stage.getRelativePointerPosition();
        setNewSelection({
            ...newSelection,
            currentX: pos.x,
            currentY: pos.y,
        });
    };

    const handleMouseUp = () => {
        if (isDragging) {
            setIsDragging(false);
        }
    };

    const performExtraction = async () => {
        console.log("🚀 performExtraction triggered");
        if (!newSelection) {
            alert("No selection found. Please select a region first.");
            return;
        }

        const x = Math.min(newSelection.startX, newSelection.currentX);
        const y = Math.min(newSelection.startY, newSelection.currentY);
        const width = Math.abs(newSelection.currentX - newSelection.startX);
        const height = Math.abs(newSelection.currentY - newSelection.startY);

        if (width <= 5 || height <= 5) {
            alert("Selected region is too small. Please select a larger area.");
            return;
        }

        setAppLoading(true);
        try {
            // Because selections are already in 'image space' thanks to getRelativePointerPosition,
            // we don't need to divide by 'scale'.
            // However, we DO need to divide by the backend render 'zoom' factor to get original PDF coordinates.
            const pdfX = x / zoom;
            const pdfY = y / zoom;
            const pdfW = width / zoom;
            const pdfH = height / zoom;

            console.log(`📡 Sending extraction request: ${pdfW}x${pdfH} at (${pdfX}, ${pdfY})`);
            const data = await extractText(file, { x: pdfX, y: pdfY, width: pdfW, height: pdfH }, pageNum);
            console.log("✅ Received data:", data);

            const selection = { x, y, width, height, ...data, id: Date.now() };
            setSelections(prev => [...prev, selection]);

            setResults(prev => {
                const newProfiles = { ...prev.profiles };
                if (data.profiles) {
                    Object.entries(data.profiles).forEach(([beam, values]) => {
                        if (!newProfiles[beam]) {
                            newProfiles[beam] = [];
                        }
                        // Add unique values only? Or all? User said "store like - W12x19(18)... (29)... (11)"
                        // Assuming we want to accumulate all found values for that beam type.
                        newProfiles[beam] = [...newProfiles[beam], ...values];
                    });
                }

                return {
                    elevations: [...new Set([...prev.elevations, ...data.elevations])],
                    studsLabelCount: (prev.studsLabelCount || 0) + data.studs_count,
                    total: (prev.total || 0) + data.studs_total,
                    profiles: newProfiles
                };
            });

            setNewSelection(null);
            alert("Extraction complete!");
        } catch (err) {
            console.error("Extraction failed:", err);
            alert("Extraction failed: " + (err.response?.data?.detail || err.message));
        }
        setAppLoading(false);
    };

    const clearResults = () => {
        setSelections([]);
        setResults({ elevations: [], total: 0, studsLabelCount: 0, profiles: {} });
    };

    const startCalibration = () => {
        setMode('calibrate');
        setCalibrationPoints([]);
    };

    useEffect(() => {
        if (calibrationPoints.length === 2) {
            const [p1, p2] = calibrationPoints;
            const dist = Math.sqrt(Math.pow(p2.x - p1.x, 2) + Math.pow(p2.y - p1.y, 2));
            const val = prompt("Enter the real-world distance (e.g., 2 for 2ft):");
            if (val) {
                setPixelsPerUnit(dist / parseFloat(val));
                alert(`Scale set: ${dist.toFixed(2)}px = ${val}${unitLabel}`);
            }
            setMode('select');
        }
    }, [calibrationPoints]);

    return (
        <div className="flex flex-col h-screen w-full bg-slate-900 text-slate-100 overflow-hidden">
            {/* Header */}
            <header className="flex items-center justify-between px-6 py-4 bg-slate-800 border-b border-slate-700">
                <div className="flex items-center gap-3">
                    <Target className="text-primary-500 w-8 h-8" />
                    <h1 className="text-xl font-bold tracking-tight">Structural Tool <span className="text-slate-400 font-normal">v2.0</span></h1>
                </div>

                <div className="flex items-center gap-4">
                    {/* Zoom Controls */}
                    <div className="flex items-center gap-2 bg-slate-700 rounded-lg p-1 mr-4">
                        <button onClick={handleZoomOut} className="p-1.5 hover:bg-slate-600 rounded text-slate-300" title="Zoom Out">
                            <span className="font-mono font-bold">-</span>
                        </button>
                        <span className="text-xs font-mono w-12 text-center select-none">{(scale * 100).toFixed(0)}%</span>
                        <button onClick={handleZoomIn} className="p-1.5 hover:bg-slate-600 rounded text-slate-300" title="Zoom In">
                            <span className="font-mono font-bold">+</span>
                        </button>
                        <button onClick={handleResetZoom} className="ml-1 p-1.5 hover:bg-slate-600 rounded text-slate-400 hover:text-white" title="Reset Zoom">
                            <RotateCcw size={14} />
                        </button>
                    </div>

                    <button
                        onClick={() => fileInputRef.current.click()}
                        className="flex items-center gap-2 bg-primary-600 hover:bg-primary-500 px-4 py-2 rounded-lg font-medium transition-all"
                    >
                        <Upload size={18} />
                        Upload PDF
                    </button>
                    <input
                        type="file"
                        ref={fileInputRef}
                        onChange={handleFileUpload}
                        className="hidden"
                        accept=".pdf"
                    />
                </div>
            </header>

            <div className="flex flex-1 overflow-hidden">
                {/* Sidebar */}
                <aside className="w-80 bg-slate-800 border-r border-slate-700 flex flex-col p-4 gap-6 overflow-y-auto">
                    {/* Controls */}
                    <section>
                        <h2 className="text-xs font-semibold text-slate-500 uppercase tracking-widest mb-3">Tools</h2>
                        <div className="grid grid-cols-2 gap-2">
                            <button
                                onClick={() => setMode('select')}
                                className={`flex items-center justify-center gap-2 p-3 rounded-lg border transition-all ${mode === 'select' ? 'bg-primary-600 border-primary-500 shadow-lg shadow-primary-900/20' : 'bg-slate-700 border-slate-600 hover:bg-slate-650'}`}
                            >
                                <FileText size={18} />
                                Selection
                            </button>
                            <button
                                onClick={startCalibration}
                                className={`flex items-center justify-center gap-2 p-3 rounded-lg border transition-all ${mode === 'calibrate' ? 'bg-primary-600 border-primary-500 shadow-lg shadow-primary-900/20' : 'bg-slate-700 border-slate-600 hover:bg-slate-650'}`}
                            >
                                <Ruler size={18} />
                                Calibrate
                            </button>
                        </div>
                    </section>

                    {/* Statistics */}
                    <section className="bg-slate-900/50 rounded-xl p-4 border border-slate-700">
                        <h2 className="text-xs font-semibold text-slate-500 uppercase tracking-widest mb-4 flex items-center justify-between">
                            Extracted Data
                            <div className="flex gap-2">
                                <button onClick={clearResults} className="hover:text-red-400 transition-colors" title="Clear all results">
                                    <Trash2 size={14} />
                                </button>
                                <Calculator size={14} />
                            </div>
                        </h2>
                        <div className="space-y-4">
                            <div className="flex justify-between items-end">
                                <span className="text-slate-400 text-sm">Total Studs (Sum):</span>
                                <span className="text-3xl font-bold text-primary-400 leading-none">{results.total}</span>
                            </div>
                            <div className="flex justify-between items-center text-sm">
                                <span className="text-slate-400">Beam Labels Count:</span>
                                <span className="text-slate-200 font-mono">{results.studsLabelCount || 0}</span>
                            </div>

                            {/* Profiles Section */}
                            {results.profiles && Object.keys(results.profiles).length > 0 && (
                                <div className="pt-4 border-t border-slate-700">
                                    <span className="text-slate-400 text-xs block mb-2 uppercase group-hover:text-primary-400 transition-colors">Profiles</span>
                                    <div className="space-y-3">
                                        {Object.entries(results.profiles).map(([beam, values]) => (
                                            <div key={beam} className="bg-slate-800 rounded-lg p-3 border border-slate-700">
                                                <div className="text-primary-400 font-bold text-sm mb-2 border-b border-slate-700 pb-1 flex justify-between">
                                                    {beam}
                                                    <span className="text-xs text-slate-500 font-normal">{values.length} items</span>
                                                </div>
                                                <div className="flex flex-wrap gap-2">
                                                    {values.map((val, idx) => (
                                                        <span key={idx} className="px-2 py-0.5 bg-slate-900 rounded text-xs border border-slate-700 text-slate-300">
                                                            ({val})
                                                        </span>
                                                    ))}
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}
                            <div className="pt-4 border-t border-slate-700">
                                <span className="text-slate-400 text-xs block mb-2 uppercase">Elevations:</span>
                                <div className="flex flex-wrap gap-2">
                                    {results.elevations.map((el, i) => (
                                        <span key={i} className="px-2 py-1 bg-slate-700 rounded text-xs border border-slate-600">
                                            {el}
                                        </span>
                                    ))}
                                    {results.elevations.length === 0 && <span className="text-slate-600 text-xs italic">none found</span>}
                                </div>
                            </div>

                            {newSelection && !isDragging && (
                                <button
                                    onClick={performExtraction}
                                    className="w-full mt-4 bg-primary-600 hover:bg-primary-500 text-white py-3 rounded-lg font-bold flex items-center justify-center gap-2 shadow-lg shadow-primary-900/20 transition-all transform active:scale-95"
                                >
                                    <Target size={18} />
                                    Process Selection
                                </button>
                            )}
                        </div>
                    </section>

                    {/* History */}
                    <section className="flex-1 overflow-hidden flex flex-col">
                        <h2 className="text-xs font-semibold text-slate-500 uppercase tracking-widest mb-3">Snapshot History</h2>
                        <div className="space-y-2 overflow-y-auto pr-2">
                            {selections.map((sel) => (
                                <div key={sel.id} className="p-3 bg-slate-700/50 rounded-lg border border-slate-650 group hover:border-primary-500 transition-colors">
                                    <div className="flex justify-between items-start mb-1">
                                        <span className="text-[10px] text-slate-500 font-mono">#{sel.id.toString().slice(-4)}</span>
                                        <button
                                            onClick={() => setSelections(selections.filter(s => s.id !== sel.id))}
                                            className="text-slate-500 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-opacity"
                                        >
                                            <Trash2 size={12} />
                                        </button>
                                    </div>
                                    <div className="text-xs">
                                        <span className="text-primary-300 font-medium">{sel.studs.length} studs</span> found
                                    </div>
                                </div>
                            ))}
                        </div>
                    </section>
                </aside>

                {/* Canvas Area */}
                <main className="flex-1 relative bg-slate-950 flex flex-col overflow-hidden">
                    {/* Pagination */}
                    <div className="absolute top-4 left-1/2 -translate-x-1/2 z-10 flex items-center gap-3 bg-slate-800/80 backdrop-blur px-4 py-2 rounded-full border border-slate-700 shadow-2xl">
                        <button
                            disabled={pageNum === 0}
                            onClick={() => { setPageNum(p => p - 1); loadPage(file, pageNum - 1); }}
                            className="p-1 hover:bg-slate-700 rounded disabled:opacity-30"
                        >
                            <ChevronLeft size={18} />
                        </button>
                        <span className="text-sm font-medium">Page {pageNum + 1}</span>
                        <button
                            onClick={() => { setPageNum(p => p + 1); loadPage(file, pageNum + 1); }}
                            className="p-1 hover:bg-slate-700 rounded"
                        >
                            <ChevronRight size={18} />
                        </button>
                    </div>

                    <div className="flex-1 overflow-auto canvas-container relative">
                        {loading && (
                            <div className="absolute inset-0 z-20 flex items-center justify-center flex-col gap-4 bg-slate-950/40 backdrop-blur-md">
                                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-500"></div>
                                <p className="text-primary-400 font-medium animate-pulse">{loadingStatus || "Working..."}</p>
                            </div>
                        )}

                        {pageImage && (
                            <Stage
                                width={pageImage.width * scale}
                                height={pageImage.height * scale}
                                scaleX={scale}
                                scaleY={scale}
                                onMouseDown={handleMouseDown}
                                onMouseMove={handleMouseMove}
                                onMouseUp={handleMouseUp}
                            >
                                <Layer>
                                    <KonvaImage image={pageImage} ref={imageRef} />

                                    {/* Past Selections */}
                                    {selections.map((sel) => (
                                        <Group key={sel.id}>
                                            <Rect
                                                x={sel.x}
                                                y={sel.y}
                                                width={sel.width}
                                                height={sel.height}
                                                stroke="#38bdf8"
                                                strokeWidth={2}
                                                dash={[5, 5]}
                                                fill="rgba(14, 165, 233, 0.2)"
                                            />
                                            <Text
                                                x={sel.x}
                                                y={sel.y - 12}
                                                text={`Studs: ${sel.studs_total}`}
                                                fill="#38bdf8"
                                                fontSize={10}
                                                fontStyle="bold"
                                            />
                                        </Group>
                                    ))}

                                    {/* Draw Current Selection (Snipping Tool Style) */}
                                    {newSelection && (
                                        <Rect
                                            x={Math.min(newSelection.startX, newSelection.currentX)}
                                            y={Math.min(newSelection.startY, newSelection.currentY)}
                                            width={Math.abs(newSelection.currentX - newSelection.startX)}
                                            height={Math.abs(newSelection.currentY - newSelection.startY)}
                                            stroke="#38bdf8"
                                            strokeWidth={2}
                                            fill="rgba(14, 165, 233, 0.2)"
                                        />
                                    )}

                                    {/* Calibration Visuals */}
                                    {calibrationPoints.map((p, i) => (
                                        <Group key={i}>
                                            <Line
                                                points={[p.x - 5, p.y, p.x + 5, p.y]}
                                                stroke="#ef4444"
                                                strokeWidth={2}
                                            />
                                            <Line
                                                points={[p.x, p.y - 5, p.x, p.y + 5]}
                                                stroke="#ef4444"
                                                strokeWidth={2}
                                            />
                                        </Group>
                                    ))}
                                    {calibrationPoints.length === 2 && (
                                        <Line
                                            points={[calibrationPoints[0].x, calibrationPoints[0].y, calibrationPoints[1].x, calibrationPoints[1].y]}
                                            stroke="#ef4444"
                                            strokeWidth={1}
                                            dash={[5, 5]}
                                        />
                                    )}
                                </Layer>
                            </Stage>
                        )}

                        {!file && !loading && (
                            <div className="absolute inset-0 flex items-center justify-center flex-col gap-4 text-slate-500">
                                <Upload size={64} className="opacity-20 translate-y-2" />
                                <p className="text-lg">Upload a structural PDF to start measuring</p>
                            </div>
                        )}
                    </div>
                </main>
            </div>
        </div>
    );
};

export default App;
