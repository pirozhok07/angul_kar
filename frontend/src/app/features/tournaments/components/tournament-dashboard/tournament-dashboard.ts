import { 
  Component,
  OnInit,
  inject,
  signal
} from '@angular/core';

import { ActivatedRoute, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router'; 
import { TournamentService } from '../../../../core/services/tournament.service';
import { Tournament } from '../../models/tournament.model';

@Component({
  imports: [RouterLink, RouterLinkActive, RouterOutlet],
  selector: 'app-tournament-dashboard',
  standalone: true,
  styleUrl: './tournament-dashboard.scss',
  templateUrl: './tournament-dashboard.html',
})
export class TournamentDashboard implements OnInit {

  private readonly route = inject(ActivatedRoute);
  private readonly tournamentService = inject(TournamentService);

  tournament = signal<Tournament | null>(null);
  loading = signal(true);
  error = signal('');

  ngOnInit(): void {
    this.route.paramMap.subscribe(params => {
      const id = Number(params.get('id'));

      if (!Number.isInteger(id) || id <= 0) {
        this.error.set('Некорректный ID турнира');
        this.loading.set(false);
        return;
      }
      this.loatTournament(id);
    });
  }
  
  loatTournament(id:number): void {
    this.loading.set(true);
    this.error.set('');

    this.tournamentService.getById(id).subscribe({
      next: data => {
        this.tournament.set(data);
        this.loading.set(false);
      },
      error: err => {
        this.error.set(
          err.status === 404
            ? 'Турнир не найден'
            : ' Не удалось загрузить турнир'
        );
        
        this.loading.set(false);
      }
    })

  }
}
