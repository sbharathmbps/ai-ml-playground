import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

@Injectable({ providedIn: 'root' })
export class ChatbotService {
  private base = environment.chatbotApiUrl;

  constructor(private http: HttpClient) {}

  chat(message: string, sessionId: string | null): Observable<ChatResponse> {
    return this.http.post<ChatResponse>(`${this.base}/chat`, { message, session_id: sessionId });
  }

  getCart(sessionId: string): Observable<CartResponse> {
    return this.http.get<CartResponse>(`${this.base}/cart/${sessionId}`);
  }

  getOrders(sessionId: string): Observable<OrdersResponse> {
    return this.http.get<OrdersResponse>(`${this.base}/orders/${sessionId}`);
  }

  getProducts(params?: { category?: string; brand?: string; min_price?: number; max_price?: number }): Observable<ProductsResponse> {
    let query = '';
    if (params) {
      const p = new URLSearchParams();
      if (params.category) p.append('category', params.category);
      if (params.brand) p.append('brand', params.brand);
      if (params.min_price != null) p.append('min_price', String(params.min_price));
      if (params.max_price != null) p.append('max_price', String(params.max_price));
      query = '?' + p.toString();
    }
    return this.http.get<ProductsResponse>(`${this.base}/products${query}`);
  }

  ping(): Observable<any> {
    return this.http.get(`${this.base}/health`);
  }

  clearSession(sessionId: string): Observable<any> {
    return this.http.delete(`${this.base}/session/${sessionId}`);
  }
}

export interface ChatResponse {
  session_id: string;
  response_type: string;
  message: string;
  data: any;
  meta: Record<string, any>;
}

export interface Product {
  id: number;
  name: string;
  brand: string;
  price: number;
  stock_qty: number;
  description: string;
  image_url: string;
  rating: number;
  category: string;
}

export interface CartItem {
  cart_item_id: number;
  product_id: number;
  name: string;
  brand: string;
  qty: number;
  unit_price: number;
  subtotal: number;
}

export interface CartResponse {
  response_type: string;
  cart_id?: number;
  data: CartItem[];
  subtotal: number;
}

export interface OrderItem {
  product_id: number;
  name: string;
  qty: number;
  unit_price: number;
  subtotal: number;
}

export interface Order {
  order_id: number;
  subtotal: number;
  tax: number;
  total: number;
  status: string;
  created_at: string;
  items: OrderItem[];
}

export interface OrdersResponse {
  response_type: string;
  total: number;
  data: Order[];
}

export interface ProductsResponse {
  response_type: string;
  total: number;
  data: Product[];
}
