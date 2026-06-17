// src/config.ts

// 开发环境：使用 Vite 代理（相对路径）
export const API_BASE_URL = '';   // 或 '/api'

export const API_ENDPOINTS = {
  chat: `${API_BASE_URL}/api/chat`,
  riskCheck: `${API_BASE_URL}/api/risk/check`,
  instructionUpload: `${API_BASE_URL}/api/instruction/upload`,
  instructionSections: `${API_BASE_URL}/api/instruction/sections`,
  health: `${API_BASE_URL}/api/health`,
};