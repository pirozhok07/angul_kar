import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class Results {
  private http = inject(HttpClient);

  private apiUrl = 'http://127.0.0.1:8000/api/tournaments';

  private url(tournamentId: number): string {
    return `${this.apiUrl}/${tournamentId}/result`;
  }

  getResults(tournamentId: number): Observable<any[]> {
    return this.http.get<any[]>(
      `${this.url(tournamentId)}`
    );
  }
  
  getCategoryResults(
    tournamentId: number,
    categoryId: number
  ): Observable<any[]> {
    return this.http.get<any[]>(
      `${this.url(tournamentId)}/${categoryId}`
    );
  }

}
