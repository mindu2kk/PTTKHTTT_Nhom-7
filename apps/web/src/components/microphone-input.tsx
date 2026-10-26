"use client";

import { useEffect, useId, useState } from "react";

const MIN_SIGNAL_RMS = 0.0001;
const SILENCE_WARNING_MS = 2000;
const METER_INTERVAL_MS = 100;
const MIN_LEVEL_DB = -80;
const MAX_LEVEL_DB = 0;

export function MicrophoneInput({
  stream,
  deviceId,
  onChange,
  disabled,
}: {
  stream: MediaStream | null;
  deviceId: string;
  onChange: (value: string) => void;
  disabled: boolean;
}) {
  const id = useId();
  const [devices, setDevices] = useState<MediaDeviceInfo[]>([]);
  const [level, setLevel] = useState(0);
  const [quiet, setQuiet] = useState(false);

  useEffect(() => {
    if (!navigator.mediaDevices?.enumerateDevices) return;
    let active = true;
    const refresh = async () => {
      try {
        const list = await navigator.mediaDevices.enumerateDevices();
        if (active)
          setDevices(list.filter((device) => device.kind === "audioinput"));
      } catch {
        /* Recording can still use the default microphone. */
      }
    };
    void refresh();
    navigator.mediaDevices.addEventListener("devicechange", refresh);
    return () => {
      active = false;
      navigator.mediaDevices.removeEventListener("devicechange", refresh);
    };
  }, [stream]);

  useEffect(() => {
    if (!stream) return;
    const context = new AudioContext();
    const source = context.createMediaStreamSource(stream);
    const analyser = context.createAnalyser();
    analyser.fftSize = 2048;
    source.connect(analyser);
    // Never connect the microphone to speakers: that would cause feedback.
    void context.resume().catch(() => {});
    const samples = new Float32Array(analyser.fftSize);
    let lastSignal = performance.now();
    const timer = setInterval(() => {
      analyser.getFloatTimeDomainData(samples);
      const rms = Math.sqrt(
        samples.reduce((sum, x) => sum + x * x, 0) / samples.length,
      );
      if (rms >= MIN_SIGNAL_RMS) lastSignal = performance.now();
      const decibels = 20 * Math.log10(rms || Number.EPSILON);
      const percentage =
        ((decibels - MIN_LEVEL_DB) / (MAX_LEVEL_DB - MIN_LEVEL_DB)) * 100;
      setLevel(Math.min(100, Math.max(0, percentage)));
      setQuiet(performance.now() - lastSignal > SILENCE_WARNING_MS);
    }, METER_INTERVAL_MS);
    return () => {
      clearInterval(timer);
      source.disconnect();
      analyser.disconnect();
      void context.close().catch(() => {});
    };
  }, [stream]);

  return (
    <div className="grid gap-2">
      <label htmlFor={id}>Micro thu âm</label>
      <select
        id={id}
        value={deviceId}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value)}
      >
        <option value="">Micro mặc định của máy</option>
        {devices
          .filter((device) => device.deviceId && device.deviceId !== "default")
          .map((device, i) => (
            <option key={device.deviceId} value={device.deviceId}>
              {device.label || `Micro ${i + 1}`}
            </option>
          ))}
      </select>
      {stream && (
        <>
          <meter
            aria-label="Mức âm micro"
            min={0}
            max={100}
            value={level}
            className="w-full"
          />
          <p role="status">
            {quiet
              ? "Chưa thấy tín hiệu micro. Hãy kiểm tra nút tắt tiếng, hoặc dừng ghi và chọn micro khác."
              : "Nói thử và kiểm tra thanh mức âm có chuyển động."}
          </p>
        </>
      )}
    </div>
  );
}
