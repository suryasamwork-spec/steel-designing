import React, { useState, useEffect } from 'react';

const COMMON_SCALES = [
    { label: '1/8" = 1\'-0"', pdfPoints: 9, realValue: 1, unit: 'ft' }, // 0.125in * 72dpi = 9pts
    { label: '1/4" = 1\'-0"', pdfPoints: 18, realValue: 1, unit: 'ft' }, // 0.25in * 72dpi = 18pts
    { label: '3/8" = 1\'-0"', pdfPoints: 27, realValue: 1, unit: 'ft' },
    { label: '1/2" = 1\'-0"', pdfPoints: 36, realValue: 1, unit: 'ft' },
    { label: '3/4" = 1\'-0"', pdfPoints: 54, realValue: 1, unit: 'ft' },
    { label: '1" = 1\'-0"', pdfPoints: 72, realValue: 1, unit: 'ft' },
    { label: '1 1/2" = 1\'-0"', pdfPoints: 108, realValue: 1, unit: 'ft' },
    { label: '3" = 1\'-0"', pdfPoints: 216, realValue: 1, unit: 'ft' },

    // Engineering
    { label: '1" = 10\'', pdfPoints: 72, realValue: 10, unit: 'ft' },
    { label: '1" = 20\'', pdfPoints: 72, realValue: 20, unit: 'ft' },
    { label: '1" = 30\'', pdfPoints: 72, realValue: 30, unit: 'ft' },
    { label: '1" = 40\'', pdfPoints: 72, realValue: 40, unit: 'ft' },
    { label: '1" = 50\'', pdfPoints: 72, realValue: 50, unit: 'ft' },
    { label: '1" = 60\'', pdfPoints: 72, realValue: 60, unit: 'ft' },
    { label: '1" = 100\'', pdfPoints: 72, realValue: 100, unit: 'ft' },
];

const PresetScalePanel = ({ onApply }) => {
    const [selectedScaleIdx, setSelectedScaleIdx] = useState(0);
    const [applied, setApplied] = useState(false);

    useEffect(() => {
        if (applied) {
            const timer = setTimeout(() => setApplied(false), 3000);
            return () => clearTimeout(timer);
        }
    }, [applied]);

    const handleApply = () => {
        const scale = COMMON_SCALES[selectedScaleIdx];
        const factor = scale.realValue / scale.pdfPoints;
        // Preset scales apply uniformly to X and Y
        onApply({ x: factor, y: factor, unit: scale.unit });
        setApplied(true);
    };

    return (
        <div className="space-y-4 p-4 bg-slate-800 rounded-lg border border-slate-700">
            <div className="space-y-2">
                <label className="text-sm text-slate-300 font-medium">Standard Scales</label>
                <select
                    className="w-full bg-slate-900 border border-slate-600 rounded p-2 text-sm focus:border-primary-500 outline-none"
                    value={selectedScaleIdx}
                    onChange={(e) => setSelectedScaleIdx(Number(e.target.value))}
                >
                    {COMMON_SCALES.map((scale, idx) => (
                        <option key={idx} value={idx}>{scale.label}</option>
                    ))}
                </select>
            </div>

            <div className="bg-slate-900/50 p-3 rounded text-xs text-slate-400">
                <div className="flex justify-between mb-1">
                    <span>Target Unit:</span>
                    <span className="text-slate-200">{COMMON_SCALES[selectedScaleIdx].unit}</span>
                </div>
                <div className="italic opacity-75">
                    Note: Assumes standard PDF scaling (72 DPI).
                </div>
            </div>

            <button
                onClick={handleApply}
                className="w-full bg-primary-600 hover:bg-primary-500 text-white py-2 rounded-lg font-medium transition-all shadow-lg shadow-primary-900/20"
            >
                {applied ? 'Scale Applied! ✅' : 'Apply Scale'}
            </button>

            {applied && (
                <div className="text-center animate-in fade-in slide-in-from-top-1">
                    <p className="text-xs text-primary-400">
                        Scale updated. Switch to <strong>Selection</strong> tool to measure.
                    </p>
                </div>
            )}
        </div>
    );
};

export default PresetScalePanel;
