import React, { useState, useEffect } from 'react';

const CustomScalePanel = ({
    points,
    onSetScale,
    onResetPoints,
    scaleFactor, // { x, y }
    unitLabel,
    setUnitLabel,
    precision,
    setPrecision
}) => {
    // Inputs for 2-point calibration
    const [distanceInput, setDistanceInput] = useState('');

    // Scale Definition State
    const [separateVertical, setSeparateVertical] = useState(false);
    const [pageUnit, setPageUnit] = useState('in'); // 'in' or 'mm'

    // Derived values for display logic
    // We want to show: [PageValue] [PageUnit] = [RealValue] [RealUnit]
    // Default PageValue to 1 for simplicity, user edits RealValue.
    // RealValue = scaleFactor * points_per_page_unit

    const POINTS_PER_INCH = 72;
    const POINTS_PER_MM = 2.83495;

    const getPointsPerUnit = (unit) => unit === 'in' ? POINTS_PER_INCH : POINTS_PER_MM;

    // Helper to calculate Real Value from ScaleFactor for a given Page Unit (assuming 1 page unit)
    const getRealFromFactor = (factor, pUnit) => {
        if (!factor) return '';
        // Factor = Real / Points
        // Real = Factor * Points
        return (factor * getPointsPerUnit(pUnit)).toFixed(4);
    };

    // Helper to calculate ScaleFactor from Real Value (assuming 1 page unit)
    const getFactorFromReal = (realVal, pUnit) => {
        const r = parseFloat(realVal);
        if (isNaN(r) || r === 0) return 0;
        // Factor = Real / Points
        return r / getPointsPerUnit(pUnit);
    };

    // Formatters
    const formatDisplay = (val) => {
        if (!val || isNaN(val)) return '';
        return parseFloat(val).toString(); // remove trailing zeros
    };

    const [applied, setApplied] = useState(false);

    useEffect(() => {
        if (applied) {
            const timer = setTimeout(() => setApplied(false), 3000);
            return () => clearTimeout(timer);
        }
    }, [applied]);

    const handleCalibrationApply = () => {
        if (points.length !== 2) return;

        const [p1, p2] = points;
        const distPx = Math.sqrt(Math.pow(p2.x - p1.x, 2) + Math.pow(p2.y - p1.y, 2));
        const distPDF = distPx / 2.0; // RENDER_ZOOM = 2.0 hardcoded in App.jsx

        const distReal = parseFloat(distanceInput);

        if (!isNaN(distReal) && distReal > 0) {
            const newScale = distReal / distPDF;
            // Apply to both X and Y unless we handle separate calibration points later
            onSetScale({ x: newScale, y: newScale, unit: unitLabel });
            setDistanceInput('');
            onResetPoints();
            setApplied(true);
        }
    };

    const handleManualChange = (axis, newVal) => {
        // newVal is the "Real World" value corresponding to "1 Page Unit"

        // If empty, pass null or don't update? 
        if (newVal === '') {
            // We can't really set scale to 0 or null easily without breaking things.
            // But we need to allow editing. 
            // Limitation: We are driving input value directly from props `scaleFactor`.
            // If we want controlled typing, we need local state for inputs.
            // For now, let's just ignore empty strings (input won't update effectively).
            // Better: use getFactorFromReal but handle empty.
            return;
        }

        const newFactor = getFactorFromReal(newVal, pageUnit);
        if (newFactor === 0) return; // invalid input

        const currentX = scaleFactor?.x || 1;
        const currentY = scaleFactor?.y || 1;

        if (axis === 'x') {
            const yToUse = separateVertical ? currentY : newFactor;
            onSetScale({ x: newFactor, y: yToUse, unit: unitLabel });
        } else { // axis === 'y'
            onSetScale({ x: currentX, y: newFactor, unit: unitLabel });
        }
    };

    // When unitLabel changes (e.g. ft -> m), we might want to default page unit?
    useEffect(() => {
        if (unitLabel === 'm' || unitLabel === 'mm') {
            setPageUnit('mm');
        } else {
            setPageUnit('in');
        }
    }, [unitLabel]);

    return (
        <div className="space-y-6">
            {/* Calibration Flow */}
            <div className="bg-slate-800 p-4 rounded-lg border border-slate-700">
                <div className="flex items-center justify-between mb-4">
                    <h3 className="text-sm font-semibold text-slate-300">Calibrate from Drawing</h3>
                    <button
                        onClick={onResetPoints}
                        className="text-xs text-primary-400 hover:text-primary-300 underline"
                    >
                        Reset Points
                    </button>
                </div>

                <div className="space-y-4">
                    {points.length === 0 && (
                        <div className="text-sm text-slate-400 italic bg-slate-900/50 p-3 rounded">
                            Click two points on the drawing to define a known distance.
                        </div>
                    )}
                    {points.length === 1 && (
                        <div className="text-sm text-primary-400 font-medium bg-primary-900/10 p-3 rounded border border-primary-500/30 animate-pulse">
                            Click the second point...
                        </div>
                    )}
                    {points.length === 2 && (
                        <div className="space-y-3 animate-in fade-in slide-in-from-top-1">
                            <div>
                                <label className="text-xs text-slate-400 uppercase font-bold">Real Distance</label>
                                <div className="flex gap-2 mt-1">
                                    <input
                                        type="number"
                                        value={distanceInput}
                                        onChange={(e) => setDistanceInput(e.target.value)}
                                        placeholder="Length"
                                        className="flex-1 bg-slate-900 border border-slate-600 rounded p-2 text-sm focus:border-primary-500 outline-none font-mono"
                                        autoFocus
                                    />
                                    <select
                                        value={unitLabel}
                                        onChange={(e) => setUnitLabel(e.target.value)}
                                        className="w-20 bg-slate-900 border border-slate-600 rounded p-2 text-sm outline-none"
                                    >
                                        <option value="ft">ft</option>
                                        <option value="in">in</option>
                                        <option value="m">m</option>
                                        <option value="mm">mm</option>
                                    </select>
                                </div>
                            </div>
                            <button
                                onClick={handleCalibrationApply}
                                disabled={!distanceInput}
                                className="w-full bg-primary-600 hover:bg-primary-500 disabled:opacity-50 disabled:cursor-not-allowed text-white py-2 rounded-lg font-medium transition-all"
                            >
                                {applied ? 'Scale Applied! ✅' : 'Apply Scale'}
                            </button>
                            {applied && (
                                <div className="text-center animate-in fade-in slide-in-from-top-1 mt-2">
                                    <p className="text-xs text-primary-400">
                                        Scale updated. Switch to <strong>Selection</strong> tool to measure.
                                    </p>
                                </div>
                            )}
                        </div>
                    )}
                </div>
            </div>

            {/* Manual Scale Definition */}
            <div className="space-y-4 border-t border-slate-700 pt-4">
                <div className="flex items-center justify-between">
                    <h3 className="text-sm font-semibold text-slate-300">Scale Definition</h3>
                    <label className="flex items-center gap-2 text-xs text-slate-400 cursor-pointer">
                        <input
                            type="checkbox"
                            checked={separateVertical}
                            onChange={(e) => setSeparateVertical(e.target.checked)}
                            className="rounded border-slate-600 bg-slate-900 text-primary-600 focus:ring-primary-500"
                        />
                        Separate Vertical
                    </label>
                </div>

                <div className="bg-slate-800 p-3 rounded-lg border border-slate-700 space-y-3">
                    {/* X Scale Input */}
                    <div>
                        <div className="flex items-center justify-between mb-1">
                            <label className="text-[10px] text-slate-400 uppercase font-bold">
                                {separateVertical ? 'X Scale' : 'Scale'}
                            </label>
                        </div>
                        <div className="flex items-center gap-2">
                            {/* Page Side */}
                            <div className="flex items-center gap-1 flex-1">
                                <span className="text-sm font-mono text-slate-300">1</span>
                                <select
                                    value={pageUnit}
                                    onChange={(e) => setPageUnit(e.target.value)}
                                    className="bg-slate-900 border-none text-slate-400 text-xs rounded py-1 px-0 w-10 text-center focus:ring-0"
                                >
                                    <option value="in">in</option>
                                    <option value="mm">mm</option>
                                </select>
                            </div>

                            <span className="text-slate-500 font-bold">=</span>

                            {/* Real Side */}
                            <div className="flex items-center gap-1 flex-[2]">
                                <input
                                    type="number"
                                    placeholder="0.00"
                                    value={scaleFactor?.x ? formatDisplay(getRealFromFactor(scaleFactor.x, pageUnit)) : ''}
                                    onChange={(e) => handleManualChange('x', e.target.value)}
                                    className="w-full bg-slate-900 border border-slate-600 rounded p-1.5 text-sm font-mono text-right focus:border-primary-500 outline-none"
                                />
                                <span className="text-xs text-primary-400 font-bold w-6">{unitLabel}</span>
                            </div>
                        </div>
                    </div>

                    {/* Y Scale Input (Conditional) */}
                    {separateVertical && (
                        <div className="pt-2 border-t border-slate-700/50">
                            <label className="text-[10px] text-slate-400 uppercase font-bold mb-1 block">Y Scale</label>
                            <div className="flex items-center gap-2">
                                <div className="flex items-center gap-1 flex-1">
                                    <span className="text-sm font-mono text-slate-300">1</span>
                                    <span className="text-xs text-slate-500">{pageUnit}</span>
                                </div>
                                <span className="text-slate-500 font-bold">=</span>
                                <div className="flex items-center gap-1 flex-[2]">
                                    <input
                                        type="number"
                                        placeholder="0.00"
                                        value={scaleFactor?.y ? formatDisplay(getRealFromFactor(scaleFactor.y, pageUnit)) : ''}
                                        onChange={(e) => handleManualChange('y', e.target.value)}
                                        className="w-full bg-slate-900 border border-slate-600 rounded p-1.5 text-sm font-mono text-right focus:border-primary-500 outline-none"
                                    />
                                    <span className="text-xs text-primary-400 font-bold w-6">{unitLabel}</span>
                                </div>
                            </div>
                        </div>
                    )}
                </div>

                <button
                    onClick={() => alert("Scale applied to all pages.")}
                    className="w-full bg-slate-700 hover:bg-slate-600 text-slate-200 py-2 rounded-lg text-xs font-medium border border-slate-600 transition-colors"
                >
                    Apply to Page Range
                </button>
            </div>

            {/* Properties & Options */}
            <div className="space-y-4 border-t border-slate-700 pt-4">
                <h3 className="text-sm font-semibold text-slate-300">Options</h3>

                <div>
                    <label className="text-xs text-slate-400 block mb-1">Precision</label>
                    <select
                        value={precision}
                        onChange={(e) => setPrecision(Number(e.target.value))}
                        className="w-full bg-slate-800 border border-slate-600 rounded p-2 text-sm focus:border-primary-500 outline-none"
                    >
                        <option value="0">0 (Integer)</option>
                        <option value="1">0.1</option>
                        <option value="2">0.01</option>
                        <option value="3">0.001</option>
                        <option value="4">0.0001</option>
                    </select>
                </div>

                {/* Placeholders */}
                <div className="opacity-50 select-none">
                    <div className="mb-2">
                        <label className="text-xs text-slate-400 block mb-1">Measurement Properties</label>
                        <div className="grid grid-cols-3 gap-2">
                            <div className="bg-slate-800 p-2 rounded border border-slate-700 text-center text-xs text-slate-500">Depth</div>
                            <div className="bg-slate-800 p-2 rounded border border-slate-700 text-center text-xs text-slate-500">Slope</div>
                            <div className="bg-slate-800 p-2 rounded border border-slate-700 text-center text-xs text-slate-500">Area</div>
                        </div>
                    </div>

                    <div>
                        <label className="text-xs text-slate-400 block mb-1">Viewports</label>
                        <div className="bg-slate-800 p-3 rounded border border-slate-700 text-xs text-slate-500 italic text-center">
                            No viewports defined
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default CustomScalePanel;
