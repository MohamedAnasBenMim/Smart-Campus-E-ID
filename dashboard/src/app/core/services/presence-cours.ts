import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { PresenceCours } from '../models/presence';

const API_BASE = 'http://localhost:8080/api';

@Injectable({ providedIn: 'root' })
export class PresenceCoursService {
  constructor(private http: HttpClient) {}

  preremplir(coursId: string, date: string): Observable<PresenceCours> {
    return this.http.get<PresenceCours>(`${API_BASE}/presence-cours/preremplir`, {
      params: { coursId, date },
    });
  }

  valider(presence: PresenceCours): Observable<PresenceCours> {
    return this.http.post<PresenceCours>(`${API_BASE}/presence-cours`, presence);
  }

  lister(coursId?: string, date?: string): Observable<PresenceCours[]> {
    const params: Record<string, string> = {};
    if (coursId) params['coursId'] = coursId;
    if (date) params['date'] = date;
    return this.http.get<PresenceCours[]>(`${API_BASE}/presence-cours`, { params });
  }
}