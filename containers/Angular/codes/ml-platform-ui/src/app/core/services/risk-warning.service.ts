import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

@Injectable({ providedIn: 'root' })
export class RiskWarningService {
  private base = environment.inferenceApiUrl;

  constructor(private http: HttpClient) {}

  uploadImage(file: File): Observable<{ image_id: string; image_path: string }> {
    const fd = new FormData();
    fd.append('file', file);
    return this.http.post<any>(`${this.base}/upload_image/`, fd);
  }

  startRiskCheck(imageId: string): Observable<{ status: string; Job_Name: string; job_id: string }> {
    return this.http.post<any>(`${this.base}/risk_warning_system/`, { image_id: imageId });
  }

  getJobStatus(jobId: string): Observable<{ status: string; progress: number }> {
    return this.http.get<any>(`${this.base}/job_status/${jobId}`);
  }

  getResults(imageId: string): Observable<RiskWarningResult> {
    return this.http.get<any>(`${this.base}/risk_warning_system/${imageId}`);
  }
}

export interface RiskWarningResult {
  image_id: string;
  image_path: string;
  risk_detected: boolean;
  risk_level: 'low' | 'medium' | 'high' | null;
  risk_factors: string[];
  explanation: string;
  sentenced_detections: Array<{ risk_factor: string; detections: { bboxes: number[][]; labels: string[] } }>;
  detections_by_risk_factor: Record<string, { bboxes: number[][]; labels: string[] }>;
}
