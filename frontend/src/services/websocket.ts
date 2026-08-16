import { ProgressUpdate } from '../types';

type ProgressCallback = (data: ProgressUpdate) => void;

export class AnalysisWebSocketService {
  private ws: WebSocket | null = null;
  private url: string;
  private onProgressCallback: ProgressCallback | null = null;
  private onErrorCallback: ((error: Event) => void) | null = null;
  private onCloseCallback: (() => void) | null = null;

  constructor(analysisId: string) {
    this.url = `ws://18.233.96.214:8081/ws/progress/${analysisId}`;
  }

  public connect(
    onProgress: ProgressCallback,
    onError?: (error: Event) => void,
    onClose?: () => void
  ) {
    this.onProgressCallback = onProgress;
    this.onErrorCallback = onError || null;
    this.onCloseCallback = onClose || null;

    try {
      this.ws = new WebSocket(this.url);

      this.ws.onmessage = (event: MessageEvent) => {
        try {
          const data: ProgressUpdate = JSON.parse(event.data);
          if (this.onProgressCallback) {
            this.onProgressCallback(data);
          }
        } catch (e) {
          console.error('Failed to parse WebSocket progress message:', e);
        }
      };

      this.ws.onerror = (event: Event) => {
        console.error('WebSocket error:', event);
        if (this.onErrorCallback) {
          this.onErrorCallback(event);
        }
      };

      this.ws.onclose = () => {
        if (this.onCloseCallback) {
          this.onCloseCallback();
        }
      };
    } catch (e) {
      console.error('Failed to establish WebSocket connection:', e);
    }
  }

  public disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}
