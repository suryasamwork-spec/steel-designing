import axios from 'axios';

const api = axios.create({
    baseURL: 'http://localhost:5001',
});

export const renderPage = async (file, pageNum = 0, zoom = 2.0) => {
    const formData = new FormData();
    formData.append('pdf', file);
    formData.append('page_num', pageNum);
    formData.append('zoom', zoom);

    const response = await api.post('/api/render-page', formData, {
        responseType: 'blob',
    });
    return URL.createObjectURL(response.data);
};

export const extractText = async (file, region, pageNum = 0) => {
    const formData = new FormData();
    formData.append('pdf', file);
    formData.append('x', region.x);
    formData.append('y', region.y);
    formData.append('width', region.width);
    formData.append('height', region.height);
    formData.append('page_num', pageNum);

    const response = await api.post('/api/extract-text', formData);
    return response.data;
};

export default api;
