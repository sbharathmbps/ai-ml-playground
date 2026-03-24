import {
  Component, ElementRef, ViewChild, OnDestroy
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatChipsModule } from '@angular/material/chips';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatDividerModule } from '@angular/material/divider';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { interval, Subscription } from 'rxjs';
import { switchMap, takeWhile } from 'rxjs/operators';
import { RiskWarningService, RiskWarningResult } from '../../core/services/risk-warning.service';

type Stage = 'upload' | 'processing' | 'results';

@Component({
  selector: 'app-risk-warning',
  standalone: true,
  imports: [
    CommonModule, FormsModule,
    MatCardModule, MatButtonModule, MatIconModule,
    MatProgressBarModule, MatChipsModule, MatCheckboxModule,
    MatSnackBarModule, MatDividerModule, MatTooltipModule,
    MatProgressSpinnerModule
  ],
  templateUrl: './risk-warning.component.html',
  styleUrl: './risk-warning.component.scss'
})
export class RiskWarningComponent implements OnDestroy {
  @ViewChild('fileInput') fileInput!: ElementRef<HTMLInputElement>;
  @ViewChild('imageEl') imageEl!: ElementRef<HTMLImageElement>;
  @ViewChild('canvas') canvasEl!: ElementRef<HTMLCanvasElement>;

  stage: Stage = 'upload';
  dragOver = false;

  // Upload state
  selectedFile: File | null = null;
  imagePreview: string | null = null;
  imageId: string | null = null;

  // Processing state
  progress = 0;
  progressSub?: Subscription;

  // Results
  result: RiskWarningResult | null = null;
  checkedFactors = new Set<string>();

  steps = [
    { title: 'Upload Image', desc: 'Select a .jpg image from your local machine' },
    { title: 'AI Risk Detection', desc: 'VLM model identifies risk factors in the scene' },
    { title: 'Object Grounding', desc: 'Each risk factor is grounded with bounding boxes' },
    { title: 'Interactive Review', desc: 'Toggle checkboxes to highlight specific hazard zones' }
  ];

  constructor(private svc: RiskWarningService, private snack: MatSnackBar) {}

  // ── Upload ─────────────────────────────────────────────────────────
  onFileSelect(event: Event) {
    const input = event.target as HTMLInputElement;
    if (input.files?.[0]) this.loadFile(input.files[0]);
  }

  onDrop(event: DragEvent) {
    event.preventDefault();
    this.dragOver = false;
    const f = event.dataTransfer?.files[0];
    if (f) this.loadFile(f);
  }

  loadFile(file: File) {
    if (!file.name.toLowerCase().endsWith('.jpg')) {
      this.snack.open('Only .jpg images are supported', 'OK', { duration: 3000, panelClass: 'error-snack' });
      return;
    }
    this.selectedFile = file;
    const reader = new FileReader();
    reader.onload = e => this.imagePreview = e.target?.result as string;
    reader.readAsDataURL(file);
  }

  uploadAndCheck() {
    if (!this.selectedFile) return;
    this.stage = 'processing';
    this.progress = 5;

    this.svc.uploadImage(this.selectedFile).subscribe({
      next: res => {
        this.imageId = res.image_id;
        this.startRiskCheck();
      },
      error: () => {
        this.snack.open('Upload failed', 'OK', { duration: 3000, panelClass: 'error-snack' });
        this.stage = 'upload';
      }
    });
  }

  startRiskCheck() {
    this.svc.startRiskCheck(this.imageId!).subscribe({
      next: () => {
        this.progress = 10;
        this.pollResults();
      },
      error: () => {
        this.snack.open('Failed to start risk check', 'OK', { duration: 3000, panelClass: 'error-snack' });
        this.stage = 'upload';
      }
    });
  }

  // Poll /risk_warning_system/{image_id} directly.
  // Completion detection:
  //   Phase 1 done: risk_detected is not null  (first pod finished)
  //   Phase 2 done: sentenced_detections.length >= risk_factors.length (second pod finished)
  //                 OR risk_detected is false (no risks → nothing to ground)
  pollResults() {
    this.progressSub = interval(2000).pipe(
      switchMap(() => this.svc.getResults(this.imageId!))
    ).subscribe({
      next: r => {
        const phase1Done = r.risk_detected !== null && r.risk_detected !== undefined;
        const noRisks = r.risk_detected === false;
        const phase2Done = noRisks ||
          (r.risk_factors?.length > 0 &&
           r.sentenced_detections?.length >= r.risk_factors.length);

        // Simulate progress
        if (!phase1Done) {
          this.progress = Math.min(this.progress + 5, 45);
        } else if (!phase2Done) {
          this.progress = Math.min(this.progress + 5, 90);
        } else {
          this.progress = 100;
          this.progressSub?.unsubscribe();
          this.result = r;
          this.stage = 'results';
        }
      },
      error: () => {
        // 404 means not ready yet — keep polling
      }
    });
  }

  // ── Bbox ───────────────────────────────────────────────────────────
  toggleFactor(factor: string, checked: boolean) {
    if (checked) this.checkedFactors.add(factor);
    else this.checkedFactors.delete(factor);
    setTimeout(() => this.redrawCanvas(), 50);
  }

  redrawCanvas() {
    const img = this.imageEl?.nativeElement;
    const canvas = this.canvasEl?.nativeElement;
    if (!img || !canvas) return;

    canvas.width = img.clientWidth;
    canvas.height = img.clientHeight;
    const ctx = canvas.getContext('2d')!;
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    if (!this.result) return;

    const scaleX = img.clientWidth / img.naturalWidth;
    const scaleY = img.clientHeight / img.naturalHeight;

    const palette = ['#e91e63','#ff5722','#ff9800','#ffd600','#76ff03','#00e5ff','#d500f9','#651fff'];
    let colorIdx = 0;

    this.checkedFactors.forEach(factor => {
      const det = this.result!.detections_by_risk_factor[factor];
      if (!det) return;
      const color = palette[colorIdx++ % palette.length];
      ctx.strokeStyle = color;
      ctx.lineWidth = 2.5;
      ctx.fillStyle = color + '33';
      ctx.font = 'bold 12px Roboto, sans-serif';

      det.bboxes.forEach((box, i) => {
        const [x1, y1, x2, y2] = box;
        const sx = x1 * scaleX, sy = y1 * scaleY;
        const sw = (x2 - x1) * scaleX, sh = (y2 - y1) * scaleY;
        ctx.fillRect(sx, sy, sw, sh);
        ctx.strokeRect(sx, sy, sw, sh);
        const label = det.labels[i] || '';
        if (label) {
          ctx.fillStyle = color;
          ctx.fillRect(sx, sy - 18, ctx.measureText(label).width + 8, 18);
          ctx.fillStyle = '#fff';
          ctx.fillText(label, sx + 4, sy - 4);
          ctx.fillStyle = color + '33';
        }
      });
    });
  }

  reset() {
    this.stage = 'upload';
    this.selectedFile = null;
    this.imagePreview = null;
    this.imageId = null;
    this.result = null;
    this.checkedFactors.clear();
    this.progress = 0;
    this.progressSub?.unsubscribe();
    if (this.fileInput) this.fileInput.nativeElement.value = '';
  }

  get riskLevelClass(): string {
    return 'chip-' + (this.result?.risk_level || 'low');
  }

  ngOnDestroy() { this.progressSub?.unsubscribe(); }
}
