import { 
  Component,
  OnInit,
  inject,
  signal
} from '@angular/core';

import {
  FormBuilder,
  ReactiveFormsModule,
  Validators
} from '@angular/forms';

import { RouterLink } from '@angular/router';
import { TournamentService } from '../../../../core/services/tournament.service';

import {
  Tournament,
  TournamentCreate
} from '../../models/tournament.model';

@Component({
  imports: [ReactiveFormsModule, RouterLink],
  selector: 'app-tournament-list',
  standalone: true,
  styleUrl: './tournament-list.scss',
  templateUrl: './tournament-list.html',
})
export class TournamentList implements OnInit {

  private readonly tournamentService = inject(TournamentService);
  private readonly fb = inject(FormBuilder);

  tournaments = signal<Tournament[]>([]);
  editingId = signal<number | null>(null);
  loading = signal(false);
  error = signal('');

  showForm = signal(false);
  tournamentForm = this.fb.nonNullable.group({
    name: ['', [Validators.required, Validators.minLength(2)]],
    location: ['', Validators.required],
    start_date: ['', Validators.required],
    end_date: ['', Validators.required],
    description: [''],
  })

  ngOnInit(): void {
    this.loadTournaments();
  }

  loadTournaments(): void {
    this.loading.set(true);
    this.error.set('');

    this.tournamentService.getAll().subscribe({
      next: (data) => {
        this.tournaments.set(data);
        this.loading.set(false);
      },
      error: () => {
        this.error.set('Не удалось загрузить турниры');
        this.loading.set(false);
      }
    });
  }

  openForm(): void {
    this.editingId.set(null);
    this.tournamentForm.reset();
    this.error.set('');
    this.showForm.set(true);
  }

  closeForm(): void {
    this.showForm.set(false);
    this.editingId.set(null);
    this.error.set('');
  }

  saveTournament(): void {
    if (this.tournamentForm.invalid) {
      this.tournamentForm.markAllAsTouched();
      return;
    }

    const data: TournamentCreate = {
      ...this.tournamentForm.getRawValue(),
      description:
        this.tournamentForm.controls.description.value || null
    };

    if (data.end_date < data.start_date) {
      this.error.set('Дата окончания раньше дата начала');
      return;
    }
    console.log(data)
    this.error.set('');
    this.loading.set(true);

    const id = this.editingId();

    const request = id !== null
      ? this.tournamentService.update(id, data)
      : this.tournamentService.create(data)

    request.subscribe({
      next: () => {
        this.closeForm();
        this.loadTournaments()
      },
      error: () => {
        this.error.set('Не удалось сохранить турнир');
        this.loading.set(false);
      }
    });
  }

  editTournament(tournament: Tournament): void {
    this.editingId.set(tournament.id);

    this.tournamentForm.patchValue({
      name: tournament.name,
      location: tournament.location,
      start_date: tournament.start_date,
      end_date: tournament.end_date,
      description: tournament.description ?? '',
    });

    this.error.set('');
    this.showForm.set(true);
  }

  deleteTournament(tournament: Tournament): void {
    const confirmed = window.confirm(
      `Удалить турнир "${tournament.name}" ?`
    );

    if (!confirmed) { return; 

    }
    this.error.set('');

    this.tournamentService.delete(tournament.id).subscribe({
      next: () => {
        this.tournaments.update(items =>
          items.filter(item => item.id !== tournament.id)
        );
      },
      error: () => {
        this.error.set('Не удалось удалить турнир');
      }
    });
  }
}
