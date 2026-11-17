import { 
  Component,
  OnInit,
  computed,
  inject,
  signal
} from '@angular/core';

import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';

import {
  Athlete,
  AthleteField,
  AthletesService
} from '../athletes.service';

import { ATHLETE_FIELD_LABELS, HIDDEN_FIELDS, HIDDEN_FIELDS_FOEM } from '../athlete-fields.maps'
import { Coach } from '../../coaches/coaches.service';
import { Club } from '../../clubs/clubs.service';

@Component({
  imports: [CommonModule, FormsModule, RouterLink],
  selector: 'app-athletes-list',
  standalone: true,
  styleUrl: './athletes-list.scss',
  templateUrl: './athletes-list.html',
})
export class AthletesList implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly service = inject(AthletesService);

  tournamentId = 0;
  athletes = signal<Athlete[]>([]);
  fields = signal<AthleteField[]>([]);
  labelFields = ATHLETE_FIELD_LABELS;
  visibleFields = computed(() => {
    return this.fields().filter(field => ! HIDDEN_FIELDS.includes(field.name))
  });
  visibleFieldsForms = computed(() => {
    return this.fields().filter(field => ! HIDDEN_FIELDS_FOEM.includes(field.name))
  });
  loading = signal(true);
  error = signal('');
  search = signal('');

  editingId = signal<number | null>(null);
  formData: Record<string, unknown> = {};
  formOpen = signal(false);
  saving = signal(false);

  coaches = signal<Coach[]>([]);
  clubs = signal<Club[]>([]);
  
  ngOnInit(): void {
    const id = Number(
      this.route.parent?.parent?.snapshot.paramMap.get('id')
    );
    
    if (!Number.isInteger(id) || id <= 0) {
      this.error.set('Не удалось определить турнир');
      this.loading.set(false);
      return;
    }

    this.tournamentId = id;
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.error.set('');

    this.service.getFields(this.tournamentId).subscribe({
      next: fields => {
        this.fields.set(fields);
        this.service.getAll(this.tournamentId).subscribe({
          next: athletes => {
            this.athletes.set(athletes);
            this.loading.set(false);
            this.loadClubs();
            this.loadCoaches();
          },
          error: () => {
            this.error.set('Не удалось загрузить атлетов');
            this.loading.set(false);
          }
        });
      },
      error: () => {
        this.error.set('Не удалось получить структуру таблицы атлетов');
        this.loading.set(false);
      }
    });
  }

  loadClubs(): void {
    this.service.getClubs(this.tournamentId).subscribe({
      next: (data) => {
        this.clubs.set(data);
      },
      error: () => {
        this.error.set('Не удалось загрузить клубы');
      }
    })
  }

  loadCoaches(): void {
    this.service.getCoaches(this.tournamentId).subscribe({
      next: (data) => {
        this.coaches.set(data);
      },
      error: () => {
        this.error.set('Не удалось загрузить тренеров');
      }
    })
  }
  
  getClubName(clubId: number | null | undefined): unknown {
    if (clubId == null) {
      return '—';
    }

    return this.clubs().find(club => club.id === clubId)?.['name'] ?? '—';
  }

  getCoachName(coachId: number | null | undefined): unknown {
    if (coachId == null) {
      return '—';
    }
    const coach = this.coaches().find(coach => coach.id === coachId)
    const full_name = (`
      ${(coach?.['last_name'] as string) ?? ''} 
      ${(coach?.['first_name'] as string)?.[0] ?? ''}.
      ${(coach?.['second_name'] as string)?.[0] ?? ''}.
    `)

    return full_name;
  }

  filteredAthletes(): Athlete[] {
    const query = this.search().trim().toLowerCase();

    if (!query) {
      return this.athletes();
    }

    return this.athletes().filter(athlete =>
      Object.values(athlete).some(value =>
        String(value ?? '').toLowerCase().includes(query)
      )
    );
  }

  openCreate(): void {
    this.editingId.set(null);
    this.formData = {};
    this.formOpen.set(true);
  }

  openEdit(athlete: Athlete): void {
    this.editingId.set(athlete.id);
    this.formData = { ...athlete };
    this.formOpen.set(true);
  }

  save(): void {
    this.saving.set(true);

    const data = { ...this.formData };
    delete data['id'];

    const request = this.editingId()
      ? this.service.update(
        this.tournamentId,
        this.editingId()!,
        data
      )
      : this.service.create(this.tournamentId, data);

    request.subscribe({
      next: () => {
        this.formOpen.set(false);
        this.saving.set(false);
        this.load();
      },
      error: err => {
        this.error.set(
          err.error?.detail || 'Не удалось сохранить атлета'
        );
        this.saving.set(false);
      }
    });
  }

  remove(athlete: Athlete): void {
    if (!confirm(`Удалить атлета №${athlete.id}?`)) {
      return;
    }

    this.service.delete(this.tournamentId, athlete.id).subscribe({
      next: () => this.load(),
      error: () => this.error.set('не удалось удалить атлета')
    });
  }

  isDateField(field: AthleteField): boolean {
    return field.type.toLowerCase().includes('date');
  }
}
