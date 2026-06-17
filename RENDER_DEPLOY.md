# Render single-service deployment

This project is configured for one Render Web Service using Docker:

- React is built with Vite during the Docker build.
- FastAPI serves both `/api/*` endpoints and the built React files.
- Render injects the public port through the `PORT` environment variable.
- The Chroma vector database is generated during the image build from `data/raw`.

## Deploy steps

1. Push this repository to GitHub.
2. In Render, choose **New +** -> **Blueprint** and select this repository.
3. Render will read `render.yaml` and create one Docker Web Service named `medsafe-agent`.
4. Add the secret environment variable:

   ```text
   QWEN_API_KEY=your_dashscope_api_key
   ```

5. Click **Apply** or **Deploy**.
6. After the deploy succeeds, Render shows a public URL like:

   ```text
   https://medsafe-agent.onrender.com
   ```

## Manual Render settings

If you do not use Blueprint, create a **Web Service** with these settings:

- Runtime: `Docker`
- Dockerfile Path: `./Dockerfile`
- Health Check Path: `/api/health`
- Environment variables:
  - `QWEN_API_KEY`: your DashScope/Qwen API key
  - `QWEN_BASE_URL`: `https://dashscope.aliyuncs.com/compatible-mode/v1`
  - `QWEN_MODEL`: `qwen-plus`
  - `OCR_ENGINE`: `easyocr`

## Notes

The OCR and embedding dependencies are still relatively large. This deployment
uses EasyOCR only and does not install PaddleOCR or PaddlePaddle.
