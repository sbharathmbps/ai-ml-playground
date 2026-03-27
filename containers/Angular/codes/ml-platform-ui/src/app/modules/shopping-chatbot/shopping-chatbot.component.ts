import {
  Component, OnInit, OnDestroy, ViewChild, ElementRef, AfterViewChecked
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatChipsModule } from '@angular/material/chips';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatBadgeModule } from '@angular/material/badge';
import { MatDividerModule } from '@angular/material/divider';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatSidenavModule } from '@angular/material/sidenav';
import { MatTabsModule } from '@angular/material/tabs';
import {
  ChatbotService, ChatResponse, Product, CartItem, Order
} from '../../core/services/chatbot.service';

interface ChatMessage {
  role: 'user' | 'bot';
  text: string;
  data?: any;
  responseType?: string;
  timestamp: Date;
  isTyping?: boolean;
  meta?: Record<string, any>;
}

@Component({
  selector: 'app-shopping-chatbot',
  standalone: true,
  imports: [
    CommonModule, FormsModule,
    MatCardModule, MatButtonModule, MatIconModule,
    MatInputModule, MatFormFieldModule, MatChipsModule,
    MatSnackBarModule, MatBadgeModule, MatDividerModule,
    MatProgressSpinnerModule, MatTooltipModule,
    MatSidenavModule, MatTabsModule
  ],
  templateUrl: './shopping-chatbot.component.html',
  styleUrl: './shopping-chatbot.component.scss'
})
export class ShoppingChatbotComponent implements OnInit, OnDestroy, AfterViewChecked {
  @ViewChild('chatScroll') chatScroll!: ElementRef<HTMLDivElement>;
  @ViewChild('msgInput') msgInput!: ElementRef<HTMLInputElement>;

  messages: ChatMessage[] = [];
  inputText = '';
  sessionId: string | null = null;
  isTyping = false;
  rightPanelOpen = true;
  rightTab = 0;

  cart: CartItem[] = [];
  cartSubtotal = 0;
  orders: Order[] = [];

  suggestions = [
    'Show me cricket bats under ₹1000',
    'Best rated football boots',
    'Add SG bat to cart',
    'What is in my cart?',
    'Show me badminton rackets',
    'Place my order'
  ];

  private shouldScroll = false;

  constructor(private svc: ChatbotService, private snack: MatSnackBar) {}

  ngOnInit() {
    this.messages.push({
      role: 'bot',
      text: '👋 Hi! I\'m your AI sports shopping assistant. Ask me anything — browse products, add items to cart, and place orders!',
      timestamp: new Date(),
      responseType: 'greeting'
    });
  }

  ngAfterViewChecked() {
    if (this.shouldScroll) {
      this.scrollToBottom();
      this.shouldScroll = false;
    }
  }

  sendMessage(text?: string) {
    const msg = (text || this.inputText).trim();
    if (!msg) return;
    this.inputText = '';

    this.messages.push({ role: 'user', text: msg, timestamp: new Date() });
    this.isTyping = true;
    this.shouldScroll = true;

    this.svc.chat(msg, this.sessionId).subscribe({
      next: res => {
        this.sessionId = res.session_id;
        this.isTyping = false;
        this.messages.push({
          role: 'bot',
          text: res.message,
          data: res.data,
          responseType: res.response_type,
          meta: res.meta,
          timestamp: new Date()
        });
        this.shouldScroll = true;
        this.handleResponseType(res);
      },
      error: () => {
        this.isTyping = false;
        this.messages.push({
          role: 'bot',
          text: 'Sorry, I encountered an error. Please try again.',
          timestamp: new Date()
        });
        this.shouldScroll = true;
      }
    });
  }

  handleResponseType(res: ChatResponse) {
    if (['cart_view', 'cart_updated', 'add_to_cart'].includes(res.response_type)) {
      this.loadCart();
    }
    if (['order_confirmed', 'order_placed'].includes(res.response_type)) {
      this.loadCart();
      this.loadOrders();
    }
  }

  loadCart() {
    if (!this.sessionId) return;
    this.svc.getCart(this.sessionId).subscribe({
      next: res => {
        this.cart = res.data || [];
        this.cartSubtotal = res.subtotal || 0;
      }
    });
  }

  loadOrders() {
    if (!this.sessionId) return;
    this.svc.getOrders(this.sessionId).subscribe({
      next: res => { this.orders = res.data || []; }
    });
  }

  clearSession() {
    if (this.sessionId) {
      this.svc.clearSession(this.sessionId).subscribe();
    }
    this.messages = [];
    this.sessionId = null;
    this.cart = [];
    this.orders = [];
    this.messages.push({
      role: 'bot',
      text: '🔄 Session cleared. Start a new conversation!',
      timestamp: new Date()
    });
  }

  scrollToBottom() {
    try {
      const el = this.chatScroll.nativeElement;
      el.scrollTop = el.scrollHeight;
    } catch {}
  }

  onEnter(event: KeyboardEvent) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      this.sendMessage();
    }
  }

  get cartCount(): number { return this.cart.reduce((s, i) => s + i.qty, 0); }

  formatPrice(p: number): string { return '₹' + p.toLocaleString('en-IN'); }

  isProductList(msg: ChatMessage): boolean {
    return msg.responseType === 'product_list' && Array.isArray(msg.data) && msg.data.length > 0;
  }

  isProductDetail(msg: ChatMessage): boolean {
    return msg.responseType === 'product_detail' && msg.data && !Array.isArray(msg.data);
  }

  isCartView(msg: ChatMessage): boolean {
    return ['cart_view', 'cart_updated'].includes(msg.responseType || '') && Array.isArray(msg.data);
  }

  isOrderConfirmed(msg: ChatMessage): boolean {
    return ['order_confirmed', 'order_placed'].includes(msg.responseType || '');
  }

  stars(rating: number): number[] {
    return Array.from({ length: Math.round(rating) }, (_, i) => i);
  }

  ngOnDestroy() {}
}
