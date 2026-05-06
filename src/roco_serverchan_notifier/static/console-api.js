export async function requestJSON(url, options = {}) {
  const response = await fetch(url, {
    headers: {"Content-Type": "application/json"},
    ...options,
  });
  const text = await response.text();
  let data = {};
  try {
    data = text ? JSON.parse(text) : {};
  } catch (error) {
    data = {message: text || "请求失败"};
  }
  if (!response.ok) throw new Error(data.detail || data.message || "请求失败");
  return data;
}
