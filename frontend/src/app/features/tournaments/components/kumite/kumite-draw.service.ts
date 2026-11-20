import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class KumiteDrawService {
  private readonly http = inject(HttpClient);
  private readonly apiUrl = 'http://127.0.0.1:8000/api/tournaments';

  private url(tournamentId: number, categoryId: number): string {
    return `${this.apiUrl}/${tournamentId}/draw/kumite/${categoryId}`;
  }

  // GET — получить жеребьёвку категории
  getAll(tournamentId: number, categoryId: number): Observable<any> {
    return this.http.get<any>(
      this.url(tournamentId, categoryId)
    );
  }

  // POST — сформировать жеребьёвку автоматически
  generate(tournamentId: number, categoryId: number): Observable<any> {
    return this.http.post<any>(
      `${this.url(tournamentId, categoryId)}/generate`,
      {}
    );
  }

  // PUT — сохранить порядок участников (старый API)
  save(
    tournamentId: number,
    categoryId: number,
    items: { athlete_id: number; position: number }[]
  ): Observable<any> {
    return this.http.put<any>(
      this.url(tournamentId, categoryId),
      { items }
    );
  }

  // PUT — сохранить расположение слотов олимпийской сетки
  saveSlots(
    tournamentId: number,
    categoryId: number,
    slots: { position: number; athlete_id: number | null }[]
  ): Observable<any> {
    return this.http.put<any>(
      `${this.url(tournamentId, categoryId)}/slots`,
      { slots }
    );
  }

  // PUT — установить или снять победителя матча
  setWinner(
    tournamentId: number,
    categoryId: number,
    matchId: number,
    winnerAthleteId: number | null
  ): Observable<any> {
    return this.http.put<any>(
      `${this.url(tournamentId, categoryId)}/matches/${matchId}/winner`,
      { winner_athlete_id: winnerAthleteId }
    );
  }
}