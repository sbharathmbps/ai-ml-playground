import { Routes } from '@angular/router';

export const routes: Routes = [
  { path: '', redirectTo: 'risk-warning', pathMatch: 'full' },
  {
    path: 'risk-warning',
    loadComponent: () => import('./modules/risk-warning/risk-warning.component').then(m => m.RiskWarningComponent)
  },
  {
    path: 'resume-intelligence',
    loadComponent: () => import('./modules/resume-intelligence/resume-intelligence.component').then(m => m.ResumeIntelligenceComponent)
  },
  {
    path: 'shopping-chatbot',
    loadComponent: () => import('./modules/shopping-chatbot/shopping-chatbot.component').then(m => m.ShoppingChatbotComponent)
  }
];
