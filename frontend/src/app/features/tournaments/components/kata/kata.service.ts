import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class KataService {
  private readonly http = inject(HttpClient);
  private readonly apiUrl = 'http://127.0.0.1:8000/api/tournaments';

  private url(tournamentId: number, categoryId: number): string {
    return `${this.apiUrl}/${tournamentId}/draw/kata/${categoryId}`;
  }

  getAll(tournamentId: number, categoryId: number): Observable<any> {
    return this.http.get<any>(
      this.url(tournamentId, categoryId)
    );
  }

  generate(tournamentId: number, categoryId: number): Observable<any> {
    return this.http.post<any>(
      `${this.url(tournamentId, categoryId)}/generate`,
      {}
    );
  }

  save(
    tournamentId: number,
    categoryId: number,
    items: any[]
  ): Observable<any> {
    return this.http.put<any>(
      this.url(tournamentId, categoryId),
      { items }
    );
  }
}