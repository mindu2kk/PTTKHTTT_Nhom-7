/* Evaluation only; recording starts on an explicit click and saves on another. */
const el = (id) => document.getElementById(id);
let cases = [], token = "", recorder, stream, timer, blob, previewUrl, generation = 0;
const status = (message) => { el("status").textContent = message; };
const tracksOff = () => { clearTimeout(timer); stream?.getTracks().forEach((track) => track.stop()); stream = undefined; };
function discard() {
  generation++;
  if (recorder?.state === "recording") recorder.stop();
  tracksOff(); recorder = undefined; blob = undefined;
  if (previewUrl) URL.revokeObjectURL(previewUrl);
  previewUrl = undefined; el("preview").removeAttribute("src"); el("preview").hidden = true;
  el("save").disabled = true; el("stop").disabled = true; el("cancel").disabled = true;
  el("sample").disabled = false; el("start").disabled = !el("consent").checked;
}
function showCase() {
  discard(); const row = cases[Number(el("sample").value)];
  el("prompt").textContent = row?.query || row?.text || row?.utterance || "Chưa có câu.";
  status("Chưa ghi âm."); el("next").disabled = !cases.length;
}
el("consent").addEventListener("change", () => {
  if (!el("consent").checked) discard();
  el("start").disabled = !el("consent").checked || !cases.length;
});
el("sample").addEventListener("change", showCase);
el("next").addEventListener("click", () => {
  el("sample").value = String((Number(el("sample").value) + 1) % cases.length); showCase();
});
el("cancel").addEventListener("click", () => { discard(); status("Đã hủy bản chưa lưu."); });
el("stop").addEventListener("click", () => {
  if (recorder?.state === "recording") recorder.stop();
  tracksOff(); el("stop").disabled = true;
});
el("start").addEventListener("click", async () => {
  discard(); const epoch = generation;
  if (!el("consent").checked) return;
  if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
    status("Trình duyệt chưa hỗ trợ ghi âm."); return;
  }
  el("start").disabled = true; el("sample").disabled = true; el("next").disabled = true;
  try {
    const acquired = await navigator.mediaDevices.getUserMedia({audio:{channelCount:1,echoCancellation:true,noiseSuppression:true,autoGainControl:true}});
    if (epoch !== generation) { acquired.getTracks().forEach((track) => track.stop()); return; }
    stream = acquired;
    const mimeType = ["audio/webm;codecs=opus","audio/ogg;codecs=opus","audio/mp4"].find((mime) => MediaRecorder.isTypeSupported(mime));
    recorder = new MediaRecorder(stream, mimeType ? {mimeType} : undefined);
    const chunks = []; let bytes = 0;
    recorder.ondataavailable = (event) => {
      if (epoch !== generation || !event.data.size) return;
      bytes += event.data.size;
      if (bytes > 2 * 1024 * 1024) { discard(); status("Bản ghi vượt 2 MB; hãy thu lại ngắn hơn."); return; }
      chunks.push(event.data);
    };
    const actualMime = recorder.mimeType;
    recorder.onstop = () => {
      tracksOff(); if (epoch !== generation) return;
      blob = new Blob(chunks, {type:actualMime}); previewUrl = URL.createObjectURL(blob);
      el("preview").src = previewUrl; el("preview").hidden = false;
      el("save").disabled = !blob.size; el("stop").disabled = true;
      status("Nghe lại rồi bấm Lưu bản ghi nếu bạn đồng ý.");
    };
    recorder.onerror = () => { discard(); status("Ghi âm bị lỗi. Vui lòng thử lại."); };
    recorder.start(250); el("stop").disabled = false; el("cancel").disabled = false;
    status("Đang ghi âm… Tự dừng sau 12 giây.");
    timer = setTimeout(() => { if (recorder?.state === "recording") recorder.stop(); tracksOff(); }, 12000);
  } catch { discard(); status("Chưa truy cập được micro. Kiểm tra quyền rồi thử lại."); }
});
el("save").addEventListener("click", async () => {
  if (!blob || !el("consent").checked) return;
  const epoch = generation; el("save").disabled = true;
  const row = cases[Number(el("sample").value)];
  try {
    const response = await fetch("/record", {method:"POST", headers:{"Content-Type":blob.type,"X-Capture-Token":token,"X-Case-Id":row.id || row.case_id,"X-Recording-Consent":"yes"}, body:blob});
    const result = await response.json(); if (epoch !== generation) return;
    if (!response.ok) throw new Error(result.detail);
    discard(); el("next").disabled = false; status(`Đã lưu. Phiên này có ${result.recordings} bản ghi.`);
  } catch (error) { if (epoch === generation) { status(error.message || "Không lưu được bản ghi."); el("save").disabled = false; } }
});
document.addEventListener("visibilitychange", () => { if (document.hidden) { discard(); status("Đã hủy bản chưa lưu khi rời trang."); } });
window.addEventListener("pagehide", discard);
fetch("/cases").then((response) => { if (!response.ok) throw new Error(); return response.json(); }).then((data) => {
  cases = data.oracle.cases; token = data.token;
  cases.forEach((row, index) => { const option = document.createElement("option"); option.value = String(index); option.textContent = row.id || row.case_id; el("sample").append(option); });
  el("sample").disabled = false; showCase();
}).catch(() => status("Không tải được bộ câu đã khóa. Hãy mở lại công cụ."));
