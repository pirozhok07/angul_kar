import {
  Component,
  OnInit,
  computed,
  inject,
  signal
} from '@angular/core';

import { CommonModule } from '@angular/common';
import { ActivatedRoute } from '@angular/router';

import { KumiteCompetitionService } from '../kumite-competition.service';

interface KumiteTatami {
  id: number;
  name: string;
  number: number;
}

interface CategoryAssignment {
  category_id: number;
  category_name: string;
  tatami_id: number | null;
}

interface CompetitionBout {
  category_id: number;
  category_name: string;
  match_id: number | null;
  bronze_match_id?: number | null;
  match_number: number;
  round_number: number;
  tatami_bout_number: number;
  bout_type: 'regular' | 'bronze' | 'final';
  stage: string;
  athlete1_id: number | null;
  athlete2_id: number | null;
  athlete1: string | null;
  athlete2: string | null;
  winner_athlete_id: number | null;
  status: string;
}

interface TatamiSchedule {
  tatami_id: number;
  tatami_name: string;
  bouts: CompetitionBout[];
}

@Component({
  selector: 'app-kumite',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './kumite.html',
  styleUrl: './kumite.scss'
})
export class Kumite implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly service = inject(KumiteCompetitionService);

  tournamentId = 0;

  tatamis = signal<KumiteTatami[]>([]);
  assignments = signal<CategoryAssignment[]>([]);
  schedule = signal<TatamiSchedule[]>([]);

  tatamiCount = signal(1);

  // true — экран настройки, false — проведение
  settingsMode = signal(true);

  // null означает все татами
  selectedTatamiId = signal<number | null>(null);

  // null означает общий список боёв
  selectedCategoryId = signal<number | null>(null);

  categoryDraw = signal<any>(null);
  categoryLoading = signal(false);

  loading = signal(false);
  saving = signal(false);
  error = signal('');
  success = signal('');

  // Все бои всех татами
  allBouts = computed(() =>
    this.schedule().flatMap(tatami =>
      tatami.bouts.map(bout => ({
        ...bout,
        tatami_id: tatami.tatami_id,
        tatami_name: tatami.tatami_name
      }))
    )
  );

  // Бои выбранного татами или всех татами
  visibleBouts = computed(() => {
    const tatamiId = this.selectedTatamiId();

    if (tatamiId === null) {
      return this.allBouts();
    }

    return this.allBouts().filter(
      bout => bout.tatami_id === tatamiId
    );
  });

  // Категории, назначенные на выбранное татами
  visibleCategories = computed(() => {
    const tatamiId = this.selectedTatamiId();

    return this.assignments().filter(item =>
      tatamiId === null || item.tatami_id === tatamiId
    );
  });

  selectedCategory = computed(() =>
    this.assignments().find(
      item => item.category_id === this.selectedCategoryId()
    ) ?? null
  );

  ngOnInit(): void {
    const id = Number(
      this.route.parent?.snapshot.paramMap.get('id')
    );

    if (!Number.isInteger(id) || id <= 0) {
      this.error.set('Некорректный ID турнира');
      return;
    }

    this.tournamentId = id;
    this.loadInitialData();
  }

  // -------------------------------------------------------
  // Загрузка
  // -------------------------------------------------------

  loadInitialData(): void {
    this.loading.set(true);
    this.error.set('');

    this.service.getTatamis(this.tournamentId).subscribe({
      next: tatamis => {
        this.tatamis.set(tatamis);
        this.tatamiCount.set(Math.max(tatamis.length, 1));
        this.loadAssignments();
      },
      error: err => this.handleError(err, 'Не удалось загрузить татами')
    });
  }

  private loadAssignments(): void {
    this.service.getAssignments(this.tournamentId).subscribe({
      next: assignments => {
        this.assignments.set(assignments);

        const configured =
          assignments.length > 0 &&
          assignments.every(item => item.tatami_id !== null) &&
          this.tatamis().length > 0;

        this.settingsMode.set(!configured);

        if (configured) {
          this.loadSchedule();
        } else {
          this.loading.set(false);
        }
      },
      error: err => this.handleError(err, 'Не удалось загрузить категории')
    });
  }

  loadSchedule(): void {
    this.loading.set(true);

    this.service.getSchedule(this.tournamentId).subscribe({
      next: schedule => {
        this.schedule.set(schedule);
        this.loading.set(false);
      },
      error: err => this.handleError(err, 'Не удалось загрузить расписание')
    });
  }

  // -------------------------------------------------------
  // Настройка татами
  // -------------------------------------------------------

  changeTatamiCount(value: number): void {
    this.tatamiCount.set(value);
  }

  saveTatamiCount(): void {
    const count = this.tatamiCount();

    if (!Number.isInteger(count) || count < 1 || count > 20) {
      this.error.set('Укажи количество татами от 1 до 20');
      return;
    }

    this.saving.set(true);
    this.error.set('');
    this.success.set('');

    this.service.setTatamiCount(
      this.tournamentId,
      count
    ).subscribe({
      next: tatamis => {
        this.tatamis.set(tatamis);
        this.saving.set(false);
        this.success.set('Количество татами сохранено');
      },
      error: err => this.handleError(err, 'Не удалось сохранить татами')
    });
  }

  assignCategory(categoryId: number, value: string): void {
    const tatamiId = value === '' ? null : Number(value);

    this.assignments.update(items =>
      items.map(item =>
        item.category_id === categoryId
          ? { ...item, tatami_id: tatamiId }
          : item
      )
    );
  }

  saveAssignments(): void {
    if (this.assignments().some(item => item.tatami_id === null)) {
      this.error.set('Распредели все категории по татами');
      return;
    }

    const payload = this.assignments().map(item => ({
      category_id: item.category_id,
      tatami_id: item.tatami_id
    }));

    this.saving.set(true);
    this.error.set('');
    this.success.set('');

    this.service.saveAssignments(
      this.tournamentId,
      payload
    ).subscribe({
      next: () => {
        this.saving.set(false);
        this.settingsMode.set(false);
        this.selectedTatamiId.set(null);
        this.selectedCategoryId.set(null);
        this.success.set('Распределение сохранено');

        this.loadSchedule();
      },
      error: err => this.handleError(err, 'Не удалось сохранить распределение')
    });
  }

  openSettings(): void {
    this.selectedCategoryId.set(null);
    this.settingsMode.set(true);
    this.success.set('');
  }

  // -------------------------------------------------------
  // Переключение татами и категорий
  // -------------------------------------------------------

  selectTatami(tatamiId: number | null): void {
    this.selectedTatamiId.set(tatamiId);
    this.selectedCategoryId.set(null);
    this.categoryDraw.set(null);
  }

  openCategory(categoryId: number): void {
    this.selectedCategoryId.set(categoryId);
    this.categoryDraw.set(null);
    this.categoryLoading.set(true);
    this.error.set('');

    this.service.getCategoryDraw(
      this.tournamentId,
      categoryId
    ).subscribe({
      next: data => {
        this.categoryDraw.set(data);
        this.categoryLoading.set(false);
      },
      error: err => {
        this.categoryLoading.set(false);
        this.handleError(err, 'Не удалось загрузить сетку категории');
      }
    });
  }

  backToSchedule(): void {
    this.selectedCategoryId.set(null);
    this.categoryDraw.set(null);
    this.loadSchedule();
  }

  // -------------------------------------------------------
  // Победители
  // -------------------------------------------------------

  setBoutWinner(
    bout: CompetitionBout,
    athleteId: number | null
  ): void {
    if (
      !athleteId ||
      !bout.match_id ||
      !bout.athlete1_id ||
      !bout.athlete2_id ||
      bout.status === 'bye' ||
      bout.status === 'empty'
    ) {
      return;
    }

    this.saving.set(true);
    this.error.set('');
    this.success.set('');

    this.service.setWinner(
      this.tournamentId,
      bout.category_id,
      bout.match_id,
      athleteId
    ).subscribe({
      next: () => {
        this.success.set('Победитель сохранён');
        this.reloadAfterResult(bout.category_id);
      },
      error: err => this.handleError(err, 'Не удалось сохранить победителя')
    });
  }

  setGridWinner(match: any, athleteId: number | null): void {
    if (!athleteId || !match?.id) {
      return;
    }
  
    const categoryId = this.selectedCategoryId();
  
    if (!categoryId) {
      return;
    }
  
    // Победитель должен быть одним из участников матча.
    const participants = [
      match.athlete1_id,
      match.athlete2_id
    ].filter((id): id is number => id != null);
  
    if (!participants.includes(athleteId)) {
      this.error.set('Выбранный спортсмен не участвует в этом бою');
      return;
    }
  
    if (match.status === 'bye' || match.status === 'empty') {
      return;
    }
  
    if (match.status === 'completed') {
      return;
    }
  
    this.saving.set(true);
    this.error.set('');
  
    this.service.setWinner(
      this.tournamentId,
      categoryId,
      match.id,
      athleteId
    ).subscribe({
      next: () => {
        this.success.set('Победитель сохранён');
        this.reloadAfterResult(categoryId);
      },
      error: err => {
        this.handleError(err, 'Не удалось сохранить победителя');
      },
      complete: () => {
        this.saving.set(false);
      }
    });
  }

  setBronzeWinner(
    bout: CompetitionBout,
    athleteId: number | null
  ): void {
    if (
      !athleteId ||
      bout.bout_type !== 'bronze' ||
      !bout.athlete1_id ||
      !bout.athlete2_id ||
      bout.status === 'completed'
    ) {
      return;
    }

    this.saving.set(true);
    this.error.set('');

    this.service.setBronzeWinner(
      this.tournamentId,
      bout.category_id,
      athleteId
    ).subscribe({
      next: () => {
        this.success.set('Результат боя за 3-е место сохранён');
        this.reloadAfterResult(bout.category_id);
      },
      error: err => this.handleError(err, 'Не удалось сохранить результат')
    });
  }

  private reloadAfterResult(categoryId: number): void {
    this.service.getSchedule(this.tournamentId).subscribe({
      next: schedule => {
        this.schedule.set(schedule);

        if (this.selectedCategoryId() === categoryId) {
          this.service.getCategoryDraw(
            this.tournamentId,
            categoryId
          ).subscribe({
            next: data => {
              this.categoryDraw.set(data);
              this.saving.set(false);
            },
            error: err => this.handleError(err, 'Не удалось обновить сетку')
          });
        } else {
          this.saving.set(false);
        }
      },
      error: err => this.handleError(err, 'Не удалось обновить расписание')
    });
  }

  // -------------------------------------------------------
  // Отображение
  // -------------------------------------------------------

  getBoutStatus(bout: CompetitionBout): string {
    if (bout.status === 'completed') {
      return 'Завершён';
    }

    if (bout.status === 'bye') {
      return 'Автоматический проход BYE';
    }

    if (bout.status === 'empty') {
      return 'Ожидание участников';
    }

    if (!bout.athlete1_id || !bout.athlete2_id) {
      return 'Ожидание участников';
    }

    return 'Ожидает проведения';
  }

  isWinner(match: any, athleteId: number | null): boolean {
    return !!athleteId &&
      match.status === 'completed' &&
      match.winner_athlete_id === athleteId;
  }

  private handleError(err: any, fallback: string): void {
    this.loading.set(false);
    this.saving.set(false);
    this.categoryLoading.set(false);
    this.error.set(err.error?.detail || fallback);
  }
  getTatamiName(tatamiId: number | null): string {
    return this.tatamis().find(
      item => item.id === tatamiId
    )?.name ?? 'Не назначено';
  }
  
  selectedCategoryBronzeBouts = computed(() =>
    this.allBouts().filter(
      bout =>
        bout.category_id === this.selectedCategoryId() &&
        bout.bout_type === 'bronze'
    )
  );
}
