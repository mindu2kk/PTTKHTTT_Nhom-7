export type SearchLaunch = {
  mode: "text" | "voice" | "image";
  query?: string;
  file?: File;
};
export const SEARCH_OPEN = "hm-search-open";
export const SEARCH_QUERY = "hm-search-query";
export function openSearch(detail: SearchLaunch) {
  window.dispatchEvent(new CustomEvent<SearchLaunch>(SEARCH_OPEN, { detail }));
}
