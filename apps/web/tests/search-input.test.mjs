import assert from "node:assert/strict";
import test from "node:test";
import {
  imageInputError,
  searchBudget,
  clipboardImage,
} from "../src/lib/search-input.ts";

for (const type of ["image/jpeg", "image/png", "image/webp"]) {
  test(`allows ${type} at exact size limit`, () => {
    assert.equal(imageInputError({ type, size: 5 * 1024 * 1024 }), "");
  });
}
for (const file of [
  { type: "image/png", size: 0 },
  { type: "image/png", size: 5 * 1024 * 1024 + 1 },
  { type: "image/svg+xml", size: 100 },
  { type: "text/html", size: 100 },
]) {
  test(`rejects image envelope ${file.type}/${file.size}`, () => {
    assert.ok(imageInputError(file));
  });
}
for (const value of [
  "-1",
  "1e6",
  "Infinity",
  "1000000000001",
  "100k",
  "",
  "3.5",
]) {
  test(`does not inherit invalid budget ${value}`, () =>
    assert.equal(searchBudget(value), ""));
}
for (const value of ["0", "500000", "1000000000000"]) {
  test(`inherits whole VND budget ${value}`, () =>
    assert.equal(searchBudget(value), value));
}
test("clipboard accepts actual image bytes, not clipboard text/URL", () => {
  const image = new File([new Uint8Array([1, 2])], "paste.png", {
    type: "image/png",
  });
  assert.equal(
    clipboardImage([
      {
        kind: "string",
        type: "text/plain",
        getAsFile: () => {
          throw new Error("must not fetch URL");
        },
      },
      { kind: "file", type: "image/png", getAsFile: () => image },
    ]),
    image,
  );
});
test("clipboard skips an unavailable image and finds next real image", () => {
  const image = new File(["bytes"], "x.webp", { type: "image/webp" });
  assert.equal(
    clipboardImage([
      { kind: "file", type: "image/png", getAsFile: () => null },
      { kind: "file", type: "image/webp", getAsFile: () => image },
    ]),
    image,
  );
});
test("plain text clipboard remains normal text input", () => {
  assert.equal(
    clipboardImage([
      { kind: "string", type: "text/plain", getAsFile: () => null },
    ]),
    null,
  );
});
