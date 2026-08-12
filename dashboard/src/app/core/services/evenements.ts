import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { EvenementAcces, AccessDecision } from '../models';

const API_BASE = 'http://localhost:8080/api';

@Injectable({ providedIn: 'root' })
export class Evenements {
  constructor(private http: HttpClient) {}

  lister(): Observable<EvenementAcces[]> {
    return this.http.get<EvenementAcces[]>(`${API_BASE}/access-events`);
  }

  tester(image: File, zoneId: string): Observable<AccessDecision[]> {
    const formData = new FormData();
    formData.append('image', image);
    formData.append('zoneId', zoneId);
    return this.http.post<AccessDecision[]>(`${API_BASE}/access-events`, formData);
  }
}