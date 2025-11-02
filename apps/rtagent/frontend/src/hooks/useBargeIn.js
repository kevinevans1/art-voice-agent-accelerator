import { useCallback } from 'react';

// Marks the most recent assistant message as interrupted when a barge-in occurs.
export const applyBargeInMarker = (messages, meta = {}) => {
  if (!Array.isArray(messages) || messages.length === 0) {
    return messages;
  }

  const updated = [...messages];
  for (let index = updated.length - 1; index >= 0; index -= 1) {
    const msg = updated[index];
    if (msg?.speaker === "Assistant") {
      if (msg.interrupted) {
        return updated;
      }

      updated[index] = {
        ...msg,
        streaming: false,
        interrupted: true,
        interruptionMeta: meta,
        text: (msg.text || "").trimEnd(),
      };
      return updated;
    }
  }

  return updated;
};

const toMs = (value) => (typeof value === "number" ? Math.round(value) : undefined);

const useBargeIn = ({
  appendLog,
  setMessages,
  setActiveSpeaker,
  assistantStreamGenerationRef,
  pcmSinkRef,
  playbackActiveRef,
  metricsRef,
  publishMetricsSummary,
}) => {
  const interruptAssistantOutput = useCallback(
    (meta, { logMessage } = {}) => {
      if (!meta) {
        return;
      }

      assistantStreamGenerationRef.current += 1;
      const logText =
        logMessage ||
        `🔇 Audio interrupted by user speech (${meta.trigger || "unknown"} → ${meta.at || "unknown"})`;
      appendLog(logText);

      if (pcmSinkRef.current) {
        pcmSinkRef.current.port.postMessage({ type: "clear" });
      }
      playbackActiveRef.current = false;

      setMessages((prev) => applyBargeInMarker(prev, meta));
      setActiveSpeaker(null);
    },
    [
      appendLog,
      assistantStreamGenerationRef,
      pcmSinkRef,
      playbackActiveRef,
      setActiveSpeaker,
      setMessages,
    ],
  );

  const recordBargeInEvent = useCallback(
    (action, meta = {}) => {
      const metrics = metricsRef.current;
      const now = performance.now();
      let event = metrics.pendingBargeIn;

      if (!event || action === "tts_cancelled") {
        event = {
          id: metrics.bargeInEvents.length + 1,
          trigger: meta.trigger,
          stage: meta.at,
          receivedTs: now,
          actions: [],
          sinceLastAudioFrameMs:
            metrics.lastAudioFrameTs != null ? now - metrics.lastAudioFrameTs : undefined,
        };
        metrics.pendingBargeIn = event;
        metrics.bargeInEvents.push(event);
      }

      event.actions.push({ action, ts: now });

      if (action === "tts_cancelled") {
        publishMetricsSummary("Barge-in tts_cancelled", {
          trigger: meta.trigger,
          stage: meta.at,
          sinceLastAudioFrameMs: toMs(event.sinceLastAudioFrameMs),
        });
      } else if (action === "audio_stop") {
        event.audioStopTs = now;
        event.timeFromCancelMs = event.receivedTs != null ? now - event.receivedTs : undefined;
        publishMetricsSummary("Barge-in audio_stop", {
          trigger: meta.trigger,
          stage: meta.at,
          deltaMs: toMs(event.timeFromCancelMs),
        });
      } else {
        publishMetricsSummary("Barge-in event", { action });
      }

      return event;
    },
    [metricsRef, publishMetricsSummary],
  );

  const finalizeBargeInClear = useCallback(
    (event, { keepPending = false } = {}) => {
      if (!event) {
        return;
      }
      const now = performance.now();
      if (event.clearIssuedTs == null) {
        event.clearIssuedTs = now;
        event.totalClearMs = event.receivedTs != null ? now - event.receivedTs : undefined;
        event.clearAfterAudioStopMs = event.audioStopTs != null ? now - event.audioStopTs : undefined;
        publishMetricsSummary("Barge-in playback cleared", {
          totalMs: toMs(event.totalClearMs),
          afterAudioStopMs: toMs(event.clearAfterAudioStopMs),
        });
      }
      metricsRef.current.pendingBargeIn = keepPending ? event : null;
    },
    [metricsRef, publishMetricsSummary],
  );

  return {
    interruptAssistantOutput,
    recordBargeInEvent,
    finalizeBargeInClear,
  };
};

export default useBargeIn;
