import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

@Injectable({ providedIn: 'root' })
export class ResumeIntelligenceService {
  private base = environment.inferenceApiUrl;

  constructor(private http: HttpClient) {}

  uploadResume(file: File): Observable<{ resume_id: string; resume_path: string }> {
    const fd = new FormData();
    fd.append('file', file);
    return this.http.post<any>(`${this.base}/upload_resume/`, fd);
  }

  extractFields(resumeId: string): Observable<{ status: string; Job_Name: string; job_id: string }> {
    return this.http.post<any>(`${this.base}/automated_field_extraction/`, { resume_id: resumeId });
  }

  getResumeFields(resumeId: string): Observable<ResumeFieldsResult> {
    return this.http.get<any>(`${this.base}/resume_fields/${resumeId}`);
  }

  saveResumeFields(resumeId: string, userField: Record<string, string>): Observable<any> {
    return this.http.put<any>(`${this.base}/resume_fields/${resumeId}`, { user_field: userField });
  }

  startRecommendation(resumeId: string): Observable<{ status: string; Job_Name: string; job_id: string }> {
    return this.http.post<any>(`${this.base}/recommendation_engine/`, { resume_id: resumeId });
  }

  getRecommendedJobs(resumeId: string): Observable<RecommendedJobsResult> {
    return this.http.get<any>(`${this.base}/recommended_jobs/${resumeId}`);
  }

  applyForJob(resumeId: string, jobId: string): Observable<any> {
    return this.http.post<any>(`${this.base}/apply_job/`, { resume_id: resumeId, job_id: jobId });
  }

  getHrApplications(status?: string): Observable<HrApplicationsResult> {
    const params = status ? `?status=${status}` : '';
    return this.http.get<any>(`${this.base}/hr_applications/${params}`);
  }

  updateApplicationStatus(applicationId: string, status: 'selected' | 'rejected'): Observable<any> {
    return this.http.put<any>(`${this.base}/hr_application_status/`, { application_id: applicationId, status });
  }

  startSalaryPrediction(resumeId: string, applicationId: string): Observable<any> {
    return this.http.post<any>(`${this.base}/salary_prediction/`, { resume_id: resumeId, application_id: applicationId });
  }

  getSalaryPrediction(applicationId: string): Observable<any> {
    return this.http.get<any>(`${this.base}/salary_prediction/${applicationId}`);
  }

  getJobStatus(jobId: string): Observable<{ status: string; progress: number }> {
    return this.http.get<any>(`${this.base}/job_status/${jobId}`);
  }
}

export interface ResumeFieldsResult {
  resume_id: string;
  extracted_field: Record<string, string>;
  user_field: Record<string, string>;
  prefilled_field: Record<string, string>;
}

export interface RecommendedJob {
  rank: string;
  job_id: string;
  description: string;
  score: number | null;
}

export interface RecommendedJobsResult {
  resume_id: string;
  recommended_jobs: any;
  recommended_jobs_mapped: RecommendedJob[];
}

export interface HrApplication {
  application_id: string;
  resume_id: string;
  job_id: string;
  market_ctc: number | null;
  status: 'applied' | 'selected' | 'rejected';
  created_at: string;
  resume_path: string;
  user_field: Record<string, string> | null;
  job_description: string;
}

export interface HrApplicationsResult {
  count: number;
  applications: HrApplication[];
}
