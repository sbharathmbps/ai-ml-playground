import { Component, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule, FormBuilder, FormGroup } from '@angular/forms';
import { MatTabsModule } from '@angular/material/tabs';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatChipsModule } from '@angular/material/chips';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatDividerModule } from '@angular/material/divider';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatSelectModule } from '@angular/material/select';
import { MatBadgeModule } from '@angular/material/badge';
import { MatTooltipModule } from '@angular/material/tooltip';
import { interval, Subscription } from 'rxjs';
import { switchMap, takeWhile } from 'rxjs/operators';
import {
  ResumeIntelligenceService,
  RecommendedJob,
  HrApplication
} from '../../core/services/resume-intelligence.service';

type EmpStage = 'upload' | 'fields' | 'jobs' | 'applied';
type HrFilter = 'all' | 'applied' | 'selected' | 'rejected';

@Component({
  selector: 'app-resume-intelligence',
  standalone: true,
  imports: [
    CommonModule, FormsModule, ReactiveFormsModule,
    MatTabsModule, MatCardModule, MatButtonModule, MatIconModule,
    MatFormFieldModule, MatInputModule, MatProgressBarModule,
    MatProgressSpinnerModule, MatChipsModule, MatSnackBarModule,
    MatDividerModule, MatExpansionModule, MatSelectModule,
    MatBadgeModule, MatTooltipModule
  ],
  templateUrl: './resume-intelligence.component.html',
  styleUrl: './resume-intelligence.component.scss'
})
export class ResumeIntelligenceComponent implements OnDestroy {

  // ── Employee state ─────────────────────────────────────────────────
  empStage: EmpStage = 'upload';
  resumeId: string | null = null;
  extracting = false;
  extractProgress = 0;
  recLoading = false;
  recProgress = 0;
  submitting = false;
  jobForm!: FormGroup;
  fieldKeys = FIELD_KEYS;
  recommendedJobs: RecommendedJob[] = [];
  selectedJob: RecommendedJob | null = null;
  appliedJobIds = new Set<string>();

  // ── HR state ───────────────────────────────────────────────────────
  hrFilter: HrFilter = 'all';
  hrApplications: HrApplication[] = [];
  hrLoading = false;
  selectedApplication: HrApplication | null = null;
  salaryLoading = false;

  private subs: Subscription[] = [];

  employeeFeatures = [
    { icon: 'auto_awesome', color: '#9c27b0', title: 'AI Field Extraction', desc: 'Automatically extract 22 profile fields from your PDF resume' },
    { icon: 'work', color: '#2196f3', title: 'Job Matching', desc: 'Get ranked job recommendations tailored to your profile' },
    { icon: 'send', color: '#4caf50', title: 'One-Click Apply', desc: 'Apply to matching jobs directly from the platform' }
  ];

  hrFilters: { label: string; value: HrFilter }[] = [
    { label: 'All', value: 'all' },
    { label: 'Applied', value: 'applied' },
    { label: 'Selected', value: 'selected' },
    { label: 'Rejected', value: 'rejected' }
  ];

  fieldDisplayKeys = FIELD_KEYS.slice(0, 12);

  constructor(
    private fb: FormBuilder,
    private svc: ResumeIntelligenceService,
    private snack: MatSnackBar
  ) {
    this.buildForm();
  }

  buildForm() {
    const controls: Record<string, any> = {};
    FIELD_KEYS.forEach(k => controls[k.key] = ['']);
    this.jobForm = this.fb.group(controls);
  }

  // ── Employee: Upload ───────────────────────────────────────────────
  onResumeFile(event: Event) {
    const f = (event.target as HTMLInputElement).files?.[0];
    if (!f) return;
    if (!f.name.toLowerCase().endsWith('.pdf')) {
      this.snack.open('Only PDF files are supported', 'OK', { duration: 3000, panelClass: 'error-snack' });
      return;
    }
    this.svc.uploadResume(f).subscribe({
      next: res => {
        this.resumeId = res.resume_id;
        this.empStage = 'fields';
        this.snack.open('Resume uploaded successfully', '', { duration: 2000, panelClass: 'success-snack' });
      },
      error: () => this.snack.open('Upload failed', 'OK', { duration: 3000, panelClass: 'error-snack' })
    });
  }

  // ── Employee: AI Extraction ────────────────────────────────────────
  extractWithAI() {
    this.extracting = true;
    this.extractProgress = 5;
    this.svc.extractFields(this.resumeId!).subscribe({
      next: () => { this.pollExtraction(); },
      error: () => { this.extracting = false; this.snack.open('Extraction failed', 'OK', { duration: 3000, panelClass: 'error-snack' }); }
    });
  }

  pollExtraction() {
    const sub = interval(2000).pipe(
      switchMap(() => this.svc.getResumeFields(this.resumeId!))
    ).subscribe({
      next: res => {
        this.extractProgress = Math.min(this.extractProgress + 10, 90);
        // Extraction done when extracted_field is populated
        if (res.extracted_field && Object.keys(res.extracted_field).length > 0) {
          this.extractProgress = 100;
          this.extracting = false;
          sub.unsubscribe();
          this.loadFields();
        }
      },
      error: () => { /* keep polling */ }
    });
    this.subs.push(sub);
  }

  loadFields() {
    this.svc.getResumeFields(this.resumeId!).subscribe({
      next: res => {
        const pf = res.prefilled_field || {};
        FIELD_KEYS.forEach(k => {
          if (pf[k.key]) this.jobForm.get(k.key)?.setValue(pf[k.key]);
        });
        this.snack.open('Fields filled from AI extraction', '', { duration: 2500, panelClass: 'success-snack' });
      }
    });
  }

  // ── Employee: Submit fields ────────────────────────────────────────
  submitFields() {
    this.submitting = true;
    const userField: Record<string, string> = {};
    FIELD_KEYS.forEach(k => userField[k.key] = this.jobForm.get(k.key)?.value || '');
    this.svc.saveResumeFields(this.resumeId!, userField).subscribe({
      next: () => {
        this.submitting = false;
        this.snack.open('Profile saved — starting AI job matching…', '', { duration: 2000, panelClass: 'success-snack' });
        this.findJobs();
      },
      error: () => { this.submitting = false; this.snack.open('Save failed', 'OK', { duration: 3000, panelClass: 'error-snack' }); }
    });
  }

  // ── Employee: Find jobs ────────────────────────────────────────────
  findJobs() {
    this.empStage = 'jobs';
    this.recLoading = true;
    this.recProgress = 5;
    this.svc.startRecommendation(this.resumeId!).subscribe({
      next: res => { this.pollJobStatus(res.job_id); },
      error: () => { this.recLoading = false; this.snack.open('Job matching failed', 'OK', { duration: 3000, panelClass: 'error-snack' }); }
    });
  }

  pollJobStatus(jobId: string) {
    const sub = interval(2000).pipe(
      switchMap(() => this.svc.getJobStatus(jobId))
    ).subscribe({
      next: res => {
        this.recProgress = res.progress ?? Math.min(this.recProgress + 8, 90);
        if (res.status === 'COMPLETED') {
          this.recProgress = 100;
          sub.unsubscribe();
          this.loadRecommendedJobs();
        }
      },
      error: () => { /* keep polling on transient errors */ }
    });
    this.subs.push(sub);
  }

  loadRecommendedJobs() {
    this.svc.getRecommendedJobs(this.resumeId!).subscribe({
      next: res => {
        this.recommendedJobs = (res.recommended_jobs_mapped || []).sort(
          (a, b) => Number(a.rank) - Number(b.rank)
        );
        this.recLoading = false;
        this.empStage = 'jobs';
      },
      error: () => { this.recLoading = false; }
    });
  }

  applyForJob(job: RecommendedJob) {
    this.svc.applyForJob(this.resumeId!, job.job_id).subscribe({
      next: () => {
        this.appliedJobIds.add(job.job_id);
        this.snack.open('Applied successfully!', '', { duration: 2000, panelClass: 'success-snack' });
      },
      error: () => this.snack.open('Application failed', 'OK', { duration: 3000, panelClass: 'error-snack' })
    });
  }

  // ── HR ──────────────────────────────────────────────────────────────
  loadHrApplications(filter: HrFilter = 'all') {
    this.hrFilter = filter;
    this.hrLoading = true;
    const status = filter === 'all' ? undefined : filter;
    this.svc.getHrApplications(status).subscribe({
      next: res => { this.hrApplications = res.applications; this.hrLoading = false; },
      error: () => { this.hrLoading = false; this.snack.open('Failed to load applications', 'OK', { duration: 3000, panelClass: 'error-snack' }); }
    });
  }

  viewApplication(app: HrApplication) {
    this.selectedApplication = app;
  }

  updateStatus(status: 'selected' | 'rejected') {
    if (!this.selectedApplication) return;
    this.svc.updateApplicationStatus(this.selectedApplication.application_id, status).subscribe({
      next: () => {
        this.snack.open(`Application ${status}`, '', { duration: 2000, panelClass: 'success-snack' });
        this.selectedApplication!.status = status;
        this.loadHrApplications(this.hrFilter);
      },
      error: () => this.snack.open('Update failed', 'OK', { duration: 3000, panelClass: 'error-snack' })
    });
  }

  calculateMarketValue() {
    if (!this.selectedApplication) return;
    this.salaryLoading = true;
    this.svc.startSalaryPrediction(
      this.selectedApplication.resume_id,
      this.selectedApplication.application_id
    ).subscribe({
      next: res => {
        if (res.market_ctc) {
          this.selectedApplication!.market_ctc = res.market_ctc;
          this.salaryLoading = false;
        } else {
          this.pollSalary();
        }
      },
      error: () => { this.salaryLoading = false; this.snack.open('Salary prediction failed', 'OK', { duration: 3000, panelClass: 'error-snack' }); }
    });
  }

  pollSalary() {
    const sub = interval(2000).pipe(
      switchMap(() => this.svc.getSalaryPrediction(this.selectedApplication!.application_id))
    ).subscribe({
      next: r => {
        if (r.market_ctc) {
          this.salaryLoading = false;
          this.selectedApplication!.market_ctc = r.market_ctc;
          sub.unsubscribe();
        }
      },
      error: () => { /* keep polling */ }
    });
    this.subs.push(sub);
  }

  onHrTabActivated() {
    if (this.hrApplications.length === 0) this.loadHrApplications();
  }

  get filteredApplications(): HrApplication[] {
    return this.hrApplications;
  }

  statusClass(status: string) { return 'chip-' + status; }

  formatCTC(ctc: number | null): string {
    if (!ctc) return '—';
    return '₹' + (ctc / 100000).toFixed(1) + ' LPA';
  }

  fieldLabel(key: string): string {
    return key.replace(/_/g, ' ');
  }

  ngOnDestroy() { this.subs.forEach(s => s.unsubscribe()); }
}

export interface FieldKey {
  key: string;
  label: string;
  type?: 'text' | 'number' | 'select';
  options?: { value: string; label: string }[];
  min?: number;
  max?: number;
}

export const FIELD_KEYS: FieldKey[] = [
  { key: 'Role',                              label: 'Role' },
  { key: 'Industry',                          label: 'Industry' },
  { key: 'Education',                         label: 'Education', type: 'select', options: [
      { value: 'Graduation', label: 'Graduation' },
      { value: 'PG',         label: 'Post Graduation (PG)' },
      { value: 'PHD',        label: 'PHD' }
  ]},
  { key: 'Department',                        label: 'Department' },
  { key: 'Designation',                       label: 'Designation' },
  { key: 'Organization',                      label: 'Organization' },
  { key: 'University_PG',                     label: 'PG University' },
  { key: 'Curent_Location',                   label: 'Current Location' },
  { key: 'University_Grad',                   label: 'Graduation University' },
  { key: 'Total_Experience',                  label: 'Total Experience (yrs)', type: 'number', min: 0, max: 50 },
  { key: 'PG_Specialization',                 label: 'PG Specialization' },
  { key: 'Passing_Year_Of_PG',               label: 'PG Passing Year', type: 'number', min: 1990, max: 2030 },
  { key: 'Graduation_Specialization',         label: 'Graduation Specialization' },
  { key: 'Passing_Year_Of_Graduation',        label: 'Graduation Passing Year', type: 'number', min: 1990, max: 2030 },
  { key: 'Total_Experience_in_field_applied', label: 'Field Experience (yrs)', type: 'number', min: 0, max: 50 },
  { key: 'Preferred_location',               label: 'Preferred Location' },
  { key: 'Current_CTC',                       label: 'Current CTC (INR)', type: 'number', min: 0 },
  { key: 'Inhand_Offer',                      label: 'In-hand Offer', type: 'select', options: [
      { value: 'Y', label: 'Yes' },
      { value: 'N', label: 'No' }
  ]},
  { key: 'Last_Appraisal_Rating',             label: 'Last Appraisal Rating', type: 'select', options: [
      { value: 'Key_Performer', label: 'Key Performer' },
      { value: 'A',             label: 'A — Exceeds Expectations' },
      { value: 'B',             label: 'B — Meets Expectations' },
      { value: 'C',             label: 'C — Below Expectations' },
      { value: 'D',             label: 'D — Needs Improvement' }
  ]},
  { key: 'No_Of_Companies_worked',            label: 'Companies Worked', type: 'number', min: 1 },
  { key: 'Number_of_Publications',            label: 'Publications', type: 'number', min: 0 },
  { key: 'Certifications',                    label: 'Certifications', type: 'number', min: 0 },
  { key: 'International_degree_any',          label: 'International Degree', type: 'select', options: [
      { value: '0', label: 'No' },
      { value: '1', label: 'Yes' }
  ]}
];
