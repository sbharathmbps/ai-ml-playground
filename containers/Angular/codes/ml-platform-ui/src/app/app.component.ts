import { Component } from '@angular/core';
import { RouterOutlet, RouterLink, RouterLinkActive } from '@angular/router';
import { MatSidenavModule } from '@angular/material/sidenav';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatListModule } from '@angular/material/list';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatTooltipModule } from '@angular/material/tooltip';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [
    CommonModule, RouterOutlet, RouterLink, RouterLinkActive,
    MatSidenavModule, MatToolbarModule, MatListModule,
    MatIconModule, MatButtonModule, MatTooltipModule
  ],
  templateUrl: './app.component.html',
  styleUrl: './app.component.scss'
})
export class AppComponent {
  sidebarExpanded = true;

  modules = [
    {
      label: 'Risk Warning System',
      route: '/risk-warning',
      icon: 'warning_amber',
      color: '#ff6b35',
      description: 'AI-powered image risk detection'
    },
    {
      label: 'Resume Intelligence',
      route: '/resume-intelligence',
      icon: 'description',
      color: '#4caf50',
      description: 'Smart resume & salary analytics'
    },
    {
      label: 'Sports Chatbot',
      route: '/shopping-chatbot',
      icon: 'sports_soccer',
      color: '#2196f3',
      description: 'AI sports gear shopping assistant'
    }
  ];

  toggleSidebar() { this.sidebarExpanded = !this.sidebarExpanded; }
}
