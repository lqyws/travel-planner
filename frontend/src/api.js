import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

export const sendMessage = (sessionId, message) =>
  api.post('/chat', { session_id: sessionId, message }).then((r) => r.data)

export const getHistory = (sessionId) =>
  api.get(`/history/${sessionId}`).then((r) => r.data)

export const listPlans = () => api.get('/plans').then((r) => r.data)

export const getPlan = (id) => api.get(`/plans/${id}`).then((r) => r.data)

export const getGallery = (city) => api.get(`/gallery/${encodeURIComponent(city)}`).then((r) => r.data)

export const listCities = () => api.get('/cities').then((r) => r.data)
