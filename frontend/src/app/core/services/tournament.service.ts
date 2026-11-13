import { Injectable, inject } from "@angular/core";
import { HttpClient } from "@angular/common/http";
import { Observable } from "rxjs";

import {
    Tournament,
    TournamentCreate
} from '../../features/tournaments/models/tournament.model'

@Injectable({ 
    providedIn: 'root'
 })
export class TournamentService {
    
    private readonly http = inject(HttpClient);

    private readonly apiUrl = 'http://127.0.0.1:8000/api/tournaments/';

    getAll(): Observable<Tournament[]> {
        return this.http.get<Tournament[]>(this.apiUrl);
    }
    
    getById(id:number): Observable<Tournament> {
        return this.http.get<Tournament>(`${this.apiUrl}${id}`);
    }

    create(data: TournamentCreate): Observable<Tournament> {
        return this.http.post<Tournament>(this.apiUrl, data);
    }

    update(id: number, data: TournamentCreate): Observable<Tournament> {
        return this.http.put<Tournament>(`${this.apiUrl}${id}`, data);
    }

    delete(id: number): Observable<Tournament> {
        return this.http.delete<Tournament>(`${this.apiUrl}${id}`);
    }

    
}