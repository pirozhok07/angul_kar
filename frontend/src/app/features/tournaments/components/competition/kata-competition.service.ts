import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class KataCompetitionService {
  private http = inject(HttpClient);

  private apiUrl = 'http://127.0.0.1:8000/api/tournaments';

  private url(tournamentId: number): string {
    return `${this.apiUrl}/${tournamentId}/kata-competition`;
  }

  private resultUrl(tournamentId: number): string {
    return `${this.apiUrl}/${tournamentId}/result`;
  }

  getCategories(tournamentId: number): Observable<any[]> {
    return this.http.get<any[]>(
      `${this.url(tournamentId)}/categories`
    );
  }

  start(tournamentId: number, categoryId: number): Observable<any> {
    return this.http.post(
      `${this.url(tournamentId)}/${categoryId}/start`,
      {}
    );
  }

  getCompetition(tournamentId: number, categoryId: number): Observable<any> {
    return this.http.get(
      `${this.url(tournamentId)}/${categoryId}`
    );
  }

  saveScores(
    tournamentId: number,
    roundId: number,
    participantId: number,
    scores: number[]
  ): Observable<any> {
    return this.http.put(
      `${this.url(tournamentId)}/rounds/${roundId}/scores/${participantId}`,
      {
        score1: scores[0],
        score2: scores[1],
        score3: scores[2],
        score4: scores[3],
        score5: scores[4]
      }
    );
  }

  finishRound(tournamentId: number, roundId: number): Observable<any> {
    return this.http.post(
      `${this.url(tournamentId)}/rounds/${roundId}/finish`,
      {}
    );
  }

  finishTiebreak(tournamentId: number, roundId: number): Observable<any> {
    return this.http.post(
      `${this.url(tournamentId)}/rounds/${roundId}/finish-tiebreak`,
      {}
    );
  }

  getResults(tournamentId: number, categoryId: number): Observable<any[]> {
    return this.http.get<any[]>(
      `${this.resultUrl(tournamentId)}/${categoryId}`
    );
  }

  getTatamis(tournamentId: number): Observable<any[]> {
    return this.http.get<any[]>(
      `${this.url(tournamentId)}/tatamis`
    );
  }
  
  getAssignments(tournamentId: number): Observable<any[]> {
    return this.http.get<any[]>(
      `${this.url(tournamentId)}/assignments`
    );
  }

  // PUT — установить количество татами
  setTatamiCount(tournamentId: number, count: number): Observable<any[]> {
    return this.http.put<any[]>(
      `${this.url(tournamentId)}/tatamis`,
      { count }
    );
  }

  saveAssignments(
    tournamentId: number,
    assignments: any[]
  ): Observable<any[]> {
    return this.http.put<any[]>(
      `${this.url(tournamentId)}/assignments`,
       assignments 
    );
  }
}
