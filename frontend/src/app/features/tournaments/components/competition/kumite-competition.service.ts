import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class KumiteCompetitionService {
  private readonly http = inject(HttpClient);
  private readonly apiUrl = 'http://127.0.0.1:8000/api/tournaments';

  private kumiteCompetitionUrl(tournamentId: number): string {
    return `${this.apiUrl}/${tournamentId}/kumite-competition`;
  }

  private url(tournamentId: number): string {
    return `${this.apiUrl}/${tournamentId}`;
  }
  private kumiteUrl(tournamentId: number, categoryId: number): string {
    return `${this.apiUrl}/${tournamentId}/draw/kumite/${categoryId}`;
  }  
  

  // GET — список татами
  getTatamis(tournamentId: number): Observable<any[]> {
    return this.http.get<any[]>(
      `${this.kumiteCompetitionUrl(tournamentId)}/tatamis`
    );
  }

  // PUT — установить количество татами
  setTatamiCount(tournamentId: number, count: number): Observable<any[]> {
    return this.http.put<any[]>(
      `${this.kumiteCompetitionUrl(tournamentId)}/tatamis`,
      { count }
    );
  }

  // GET — категории и назначенные татами
  getAssignments(tournamentId: number): Observable<any[]> {
    return this.http.get<any[]>(
      `${this.kumiteCompetitionUrl(tournamentId)}/assignments`
    );
  }

  // PUT — сохранить распределение категорий
  saveAssignments(
    tournamentId: number,
    assignments: { category_id: number; tatami_id: number | null }[]
  ): Observable<any> {
    return this.http.put<any>(
      `${this.kumiteCompetitionUrl(tournamentId)}/assignments`,
      { assignments }
    );
  }

  // GET — расписание всех татами
  getSchedule(tournamentId: number): Observable<any[]> {
    return this.http.get<any[]>(
      `${this.kumiteCompetitionUrl(tournamentId)}/schedule`
    );
  }

  // GET — получить сетку выбранной категории
  getCategoryDraw(tournamentId: number, categoryId: number): Observable<any> {
    return this.http.get<any>(
      this.kumiteUrl(tournamentId, categoryId)
    );
  }

  // PUT — записать победителя обычного боя
  setWinner(
    tournamentId: number,
    categoryId: number,
    matchId: number,
    winnerAthleteId: number
  ): Observable<any> {
    return this.http.put<any>(
      `${this.kumiteUrl(tournamentId, categoryId)}/matches/${matchId}/winner`,
      { winner_athlete_id: winnerAthleteId }
    );
  }

  // PUT — записать победителя боя за 3-е место
  setBronzeWinner(
    tournamentId: number,
    categoryId: number,
    winnerAthleteId: number
  ): Observable<any> {
    return this.http.put<any>(
      `${this.kumiteCompetitionUrl(tournamentId)}/bronze/${categoryId}/winner`,
      { winner_athlete_id: winnerAthleteId }
    );
  }

  getResults(tournamentId: number): Observable<any[]> {
    return this.http.get<any[]>(
      `${this.url(tournamentId)}/results`
    );
  }
  
  getCategoryResults(
    tournamentId: number,
    categoryId: number
  ): Observable<any[]> {
    return this.http.get<any[]>(
      `${this.url(tournamentId)}/results/${categoryId}`
    );
  }
  
  finalizeCategory(
    tournamentId: number,
    categoryId: number
  ): Observable<any> {
    return this.http.post<any>(
      `${this.url(tournamentId)}/results/${categoryId}/finalize`,
      {}
    );
  }
}
