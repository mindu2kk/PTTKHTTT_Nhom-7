// A narrow port for the experimental on-device Web Speech API. Never use cloud mode.
export type SpeechAvailability =
  "available" | "downloadable" | "downloading" | "unavailable";
export type LocalSpeech = {
  lang: string;
  processLocally: boolean;
  continuous: boolean;
  interimResults: boolean;
  onresult:
    | ((event: {
        results: ArrayLike<ArrayLike<{ transcript: string }>>;
      }) => void)
    | null;
  onerror: ((event: { error: string }) => void) | null;
  onend: (() => void) | null;
  start(): void;
  stop(): void;
  abort(): void;
};
type SpeechConstructor = {
  new (): LocalSpeech;
  prototype: LocalSpeech;
  available(options: {
    langs: string[];
    processLocally: true;
  }): Promise<SpeechAvailability>;
  install(options: { langs: string[]; processLocally: true }): Promise<boolean>;
};
export const localSpeechOptions = {
  langs: ["vi-VN"],
  processLocally: true as const,
};
export function localSpeechConstructor(): SpeechConstructor | undefined {
  const browser = window as unknown as {
    SpeechRecognition?: SpeechConstructor;
    webkitSpeechRecognition?: SpeechConstructor;
  };
  const Speech = browser.SpeechRecognition || browser.webkitSpeechRecognition;
  return window.isSecureContext &&
    Speech &&
    "processLocally" in Speech.prototype &&
    typeof Speech.available === "function" &&
    typeof Speech.install === "function"
    ? Speech
    : undefined;
}
