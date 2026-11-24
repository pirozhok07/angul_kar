import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import {
  CdkDragDrop,
  DragDropModule,
  moveItemInArray
} from '@angular/cdk/drag-drop';

import { KataCompetitionService } from '../kata-competition.service';

@Component({
  selector: 'app-kata',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    DragDropModule
  ],
  templateUrl: './kata.html',
  styleUrl: './kata.scss'
})
export class Kata implements OnInit {
  private route = inject(ActivatedRoute);
  private service = inject(KataCompetitionService);

  tournamentId = 0;

  // Данные
  athletes = signal<any[]>([]);
  categories = signal<any[]>([]);
  tatamis = signal<any[]>([]);
  assignments = signal<any[]>([]);

  // Назначения и порядок
  assignmentDraft = signal<Record<number, number | null>>({});
  categoryOrder = signal<Record<number, number[]>>({});

  // Соревнования
  competitions = signal<Record<number, any>>({});
  resultsByCategory = signal<Record<number, any[]>>({});
  selectedRounds = signal<Record<number, number | null>>({});
  scoreValues = signal<Record<string, number[]>>({});

  // Интерфейс
  openCategories = signal<Record<number, boolean>>({});
  selectedTatamiId = signal<number | null>(null);

  tatamiCount = signal(1);
  settingsMode = signal(true);

  loading = signal(false);
  saving = signal(false);
  assignmentsSaving = signal(false);

  error = signal('');
  success = signal('');

  // Нераспределённые категории
  unassignedCategories = computed(() =>
    this.assignments().filter(
      category => category.tatami_id == null
    )
  );

  // Категории каждого татами с учётом порядка
  tatamiCategories = computed(() => {
    const result: Record<number, any[]> = {};

    for (const tatami of this.tatamis()) {
      const categories = this.assignments().filter(
        category =>
          Number(category.tatami_id) === Number(tatami.id)
      );

      const order = this.categoryOrder()[tatami.id] ?? [];

      result[tatami.id] = [...categories].sort((a, b) => {
        const indexA = order.indexOf(Number(a.category_id));
        const indexB = order.indexOf(Number(b.category_id));

        if (indexA === -1 && indexB === -1) {
          return (a.position ?? 0) - (b.position ?? 0);
        }

        if (indexA === -1) return 1;
        if (indexB === -1) return -1;

        return indexA - indexB;
      });
    }

    return result;
  });

  // Группы татами для рабочего режима
  tatamiGroups = computed(() =>
    this.tatamis().map(tatami => ({
      ...tatami,
      categories: this.assignments()
        .filter(category =>
          Number(category.kata_tatami_id) === Number(tatami.id)
        )
        .sort((a, b) =>
          (a.position ?? 0) - (b.position ?? 0)
        )
    }))
  );

  // ─────────────────────────────
  // Инициализация
  // ─────────────────────────────

  ngOnInit(): void {
    this.tournamentId = Number(
      this.route.parent?.snapshot.paramMap.get('id')
    );

    this.loadSchedule();
    this.loadTatamiAssignments();
  }

  loadSchedule(): void {
    this.loading.set(true);
    this.error.set('');

    this.service.getCategories(this.tournamentId).subscribe({
      next: (data: any[]) => {
        this.categories.set(data ?? []);
        this.loading.set(false);
        this.loadAssignments();
      },
      error: (err: any) => {
        this.loading.set(false);
        this.handleError(err);
      }
    });
  }

  loadCategories(): void {
    this.loadSchedule();
  }

  // ─────────────────────────────
  // Загрузка татами и назначений
  // ─────────────────────────────

  loadTatamiAssignments(): void {
    this.service.getTatamis(this.tournamentId).subscribe({
      next: (data: any[]) => {
        this.tatamis.set(data ?? []);
        this.tatamiCount.set(data?.length ?? 1);

        if (this.categories().length) {
          this.loadAssignments();
        }
      },
      error: (err: any) => this.handleError(err)
    });
  }

  loadAssignments(): void {
    this.service.getAssignments(this.tournamentId).subscribe({
      next: (data: any[]) => {
        const apiAssignments = data ?? [];
        const assignmentMap = new Map<number, any>();

        apiAssignments.forEach(item => {
          assignmentMap.set(Number(item.category_id), item);
        });

        const configured =
        data.length > 0 &&
        data.every(item => item.tatami_id !== null) &&
        this.tatamis().length > 0;

        this.settingsMode.set(!configured);
        // Объединяем все категории с назначениями из API
        const allCategories = this.categories().map(category => {
          const categoryId = Number(
            category.category_id ?? category.id
          );

          const assignment = assignmentMap.get(categoryId);

          return {
            ...category,
            ...assignment,
            category_id: categoryId,
            tatami_id: assignment?.tatami_id ?? null,
            position: assignment?.position ?? null
          };
        });

        this.assignments.set(allCategories);

        const draft: Record<number, number | null> = {};

        allCategories.forEach(category => {
          draft[category.category_id] = category.tatami_id;
        });

        this.assignmentDraft.set(draft);

        // Восстанавливаем порядок из API
        const order: Record<number, number[]> = {};

        this.tatamis().forEach(tatami => {
          order[tatami.id] = allCategories
            .filter(item =>
              Number(item.tatami_id) === Number(tatami.id)
            )
            .sort((a, b) =>
              (a.position ?? 0) - (b.position ?? 0)
            )
            .map(item => Number(item.category_id));
        });

        this.categoryOrder.set(order);
      },
      error: (err: any) => this.handleError(err)
    });
  }

  // ─────────────────────────────
  // Drag & Drop
  // ─────────────────────────────

  dropCategory(
    event: CdkDragDrop<any[]>,
    tatamiId: number | null
  ): void {
    const category = event.item.data;

    if (!category) return;

    const categoryId = Number(
      category.category_id ?? category.id
    );

    if (!categoryId) return;

    // Перемещение внутри одного татами
    if (event.previousContainer === event.container) {
      if (tatamiId === null) return;

      const currentOrder = [
        ...(this.categoryOrder()[tatamiId] ?? [])
      ];

      // Если порядок ещё не был инициализирован
      if (!currentOrder.length) {
        currentOrder.push(
          ...this.assignments()
            .filter(item =>
              Number(item.tatami_id) === Number(tatamiId)
            )
            .map(item => Number(item.category_id))
        );
      }

      const oldIndex = currentOrder.indexOf(categoryId);

      if (oldIndex !== -1) {
        moveItemInArray(
          currentOrder,
          oldIndex,
          event.currentIndex
        );
      }

      this.categoryOrder.update(current => ({
        ...current,
        [tatamiId]: currentOrder
      }));

      this.updatePositions();
      return;
    }

    // Перемещение между списками
    const updated = this.assignments().map(item => ({
      ...item
    }));

    const index = updated.findIndex(
      item => Number(item.category_id) === categoryId
    );

    if (index === -1) return;

    updated[index] = {
      ...updated[index],
      tatami_id: tatamiId
    };

    this.assignments.set(updated);

    this.assignmentDraft.update(current => ({
      ...current,
      [categoryId]: tatamiId
    }));

    // Убираем категорию из старых списков порядка
    this.categoryOrder.update(current => {
      const result = { ...current };

      Object.keys(result).forEach(key => {
        result[Number(key)] = result[Number(key)].filter(
          id => id !== categoryId
        );
      });

      // Добавляем категорию в новый татами
      if (tatamiId !== null) {
        const order = [...(result[tatamiId] ?? [])];

        const targetIndex = Math.min(
          event.currentIndex,
          order.length
        );

        order.splice(targetIndex, 0, categoryId);
        result[tatamiId] = order;
      }

      return result;
    });

    this.updatePositions();
  }

  // Обновляем position в assignments
  private updatePositions(): void {
    const order = this.categoryOrder();

    this.assignments.update(items =>
      items.map(item => {
        const tatamiId = item.tatami_id;

        if (tatamiId == null) {
          return {
            ...item,
            position: null
          };
        }

        const ids = order[tatamiId] ?? [];
        const position = ids.indexOf(
          Number(item.category_id)
        );

        return {
          ...item,
          position: position === -1 ? ids.length + 1 : position + 1
        };
      })
    );
  }

  // ─────────────────────────────
  // Настройка количества татами
  // ─────────────────────────────

  openSettings(): void {
    this.settingsMode.set(true);
    this.success.set('');
    this.error.set('');
  }

  changeTatamiCount(value: number): void {
    this.tatamiCount.set(Number(value));
  }

  saveTatamiCount(): void {
    this.saving.set(true);
    this.error.set('');
    this.success.set('');

    this.service.setTatamiCount(
      this.tournamentId,
      this.tatamiCount()
    ).subscribe({
      next: () => {
        this.saving.set(false);
        this.loadTatamiAssignments();
        this.success.set('Количество татами сохранено');
      },
      error: (err: any) => {
        this.saving.set(false);
        this.handleError(err);
      }
    });
  }

  // ─────────────────────────────
  // Сохранение распределения
  // ─────────────────────────────

  assignCategory(
    categoryId: number,
    tatamiId: number | null
  ): void {
    this.assignmentDraft.update(current => ({
      ...current,
      [categoryId]: tatamiId
    }));
  }

  saveAssignments(): void {
    this.assignmentsSaving.set(true);
    this.error.set('');
    this.success.set('');

    const payload = this.assignments().map(category => {
      const tatamiId =
        this.assignmentDraft()[category.category_id] ?? null;

      const order = tatamiId
        ? this.categoryOrder()[tatamiId] ?? []
        : [];

      return {
        category_id: category.category_id,
        kata_tatami_id: tatamiId,
        position: tatamiId
          ? Math.max(
              0,
              order.indexOf(Number(category.category_id))
            ) + 1
          : null
      };
    });

    this.service.saveAssignments(
      this.tournamentId,
      payload
    ).subscribe({
      next: () => {
        this.assignmentsSaving.set(false);
        this.loadAssignments();
        this.settingsMode.set(false);
        this.success.set('Распределение и порядок сохранены');
      },
      error: (err: any) => {
        this.assignmentsSaving.set(false);
        this.handleError(err);
      }
    });
  }

  // ─────────────────────────────
  // Фильтр татами
  // ─────────────────────────────

  selectTatami(tatamiId: number | null): void {
    this.selectedTatamiId.set(tatamiId);
  }

  visibleTatamis(): any[] {
    const groups = this.tatamiGroups();

    if (this.selectedTatamiId() === null) {
      return groups;
    }

    return groups.filter(
      tatami => Number(tatami.id) === Number(this.selectedTatamiId())
    );
  }

  // ─────────────────────────────
  // Соревнования по категориям
  // ─────────────────────────────

  isCategoryOpen(categoryId: number): boolean {
    return !!this.openCategories()[categoryId];
  }

  competitionFor(categoryId: number): any {
    return this.competitions()[categoryId] ?? null;
  }

  roundsFor(categoryId: number): any[] {
    return this.competitionFor(categoryId)?.rounds ?? [];
  }

  activeRoundId(categoryId: number): number | null {
    return this.selectedRounds()[categoryId] ?? null;
  }

  activeRoundFor(categoryId: number): any {
    const rounds = this.roundsFor(categoryId);
    const roundId = this.activeRoundId(categoryId);

    return rounds.find(
      (round: any) => round.id === roundId
    ) ?? rounds[0] ?? null;
  }

  openCategory(categoryId: number): void {
    const isOpen = this.isCategoryOpen(categoryId);

    this.openCategories.update(current => ({
      ...current,
      [categoryId]: !isOpen
    }));

    if (isOpen) return;

    if (!this.competitionFor(categoryId)) {
      this.service.start(
        this.tournamentId,
        categoryId
      ).subscribe({
        next: () => this.loadCompetition(categoryId),
        error: (err: any) => this.handleError(err)
      });
    } else {
      this.loadCompetition(categoryId);
    }
  }

  loadCompetition(categoryId: number): void {
    this.service.getCompetition(
      this.tournamentId,
      categoryId
    ).subscribe({
      next: (data: any) => {
        this.competitions.update(current => ({
          ...current,
          [categoryId]: data
        }));

        const rounds = data?.rounds ?? [];

        if (rounds.length > 0) {
          const selected = this.selectedRounds()[categoryId];

          if (!rounds.some((round: any) => round.id === selected)) {
            this.selectedRounds.update(current => ({
              ...current,
              [categoryId]: rounds[0].id
            }));
          }
        }

        this.loadResults(categoryId);
      },
      error: (err: any) => this.handleError(err)
    });
  }

  selectRound(categoryId: number, roundId: number): void {
    this.selectedRounds.update(current => ({
      ...current,
      [categoryId]: roundId
    }));
  }

  // ─────────────────────────────
  // Оценки судей
  // ─────────────────────────────

  private scoreKey(
    categoryId: number,
    roundId: number,
    participantId: number
  ): string {
    return `${categoryId}_${roundId}_${participantId}`;
  }

  getScores(
    categoryId: number,
    participantId: number
  ): number[] {
    const round = this.activeRoundFor(categoryId);

    if (!round) {
      return [6, 6, 6, 6, 6];
    }

    const key = this.scoreKey(
      categoryId,
      round.id,
      participantId
    );

    const cached = this.scoreValues()[key];

    if (cached) return cached;

    const participant = round.participants?.find(
      (item: any) => item.id === participantId
    );

    const saved = participant?.scores;

    if (saved) {
      return [
        saved.score1 ?? 6,
        saved.score2 ?? 6,
        saved.score3 ?? 6,
        saved.score4 ?? 6,
        saved.score5 ?? 6
      ];
    }

    return [6, 6, 6, 6, 6];
  }

  getScoreClass(scores: number[], index: number): string {
    if (!scores || scores.length === 0) return '';
    
    const min = Math.min(...scores);
    const max = Math.max(...scores);

    const minIndex = scores.indexOf(min);
    const maxIndex = min === max 
      ? scores.length - 1
      : scores.indexOf(max);

    if (index === minIndex) return 'min-score';
    if (index === maxIndex) return 'max-score';
    
    return '';
  }

  updateScore(
    categoryId: number,
    participantId: number,
    judgeIndex: number,
    value: number
  ): void {
    const round = this.activeRoundFor(categoryId);
    if (!round) return;

    const key = this.scoreKey(
      categoryId,
      round.id,
      participantId
    );

    const scores = [
      ...this.getScores(categoryId, participantId)
    ];

    scores[judgeIndex] = Number(value);

    this.scoreValues.update(current => ({
      ...current,
      [key]: scores
    }));
  }

  calculateTotal(scores: number[]): number {
    if (!scores || scores.length !== 5) return 0;

    const sorted = [...scores].sort((a, b) => a - b);

    return Number(
      sorted.slice(1, 4)
        .reduce((sum, value) => sum + value, 0)
        .toFixed(2)
    );
  }

  saveScores(
    categoryId: number,
    roundId: number,
    participantId: number
  ): void {
    const key = this.scoreKey(
      categoryId,
      roundId,
      participantId
    );

    const scores = this.scoreValues()[key]
      ?? this.getScores(categoryId, participantId);

    this.saving.set(true);
    this.error.set('');
    this.success.set('');

    this.service.saveScores(
      this.tournamentId,
      roundId,
      participantId,
      scores
    ).subscribe({
      next: () => {
        this.saving.set(false);
        this.success.set('Оценки сохранены');
        this.loadCompetition(categoryId);
      },
      error: (err: any) => {
        this.saving.set(false);
        this.handleError(err);
      }
    });
  }

  // ─────────────────────────────
  // Завершение раунда
  // ─────────────────────────────

  finishRound(categoryId: number, roundId: number): void {
    const competition = this.competitionFor(categoryId);
    const round = competition?.rounds?.find(
      (r: any) => Number(r.id) === Number(roundId)
    );
  
    if (!round) return;
  
    this.saving.set(true);
    this.error.set('');
    this.success.set('');
  
    // Если это дополнительный круг — завершаем тай-брейк
    if (round.round_type === 'tiebreak') {
      this.service.finishTiebreak(
        this.tournamentId,
        roundId
      ).subscribe({
        next: () => {
          this.saving.set(false);
          this.loadCompetition(categoryId);
          this.loadResults(categoryId);
        },
        error: (err: any) => {
          this.saving.set(false);
          this.handleError(err);
        }
      });
  
      return;
    }
  
    // Обычный круг
    this.service.finishRound(
      this.tournamentId,
      roundId
    ).subscribe({
      next: (data: any) => {
        this.saving.set(false);
  
        // Если возникла ничья — загружаем дополнительный круг
        // НЕ завершаем его автоматически!
        if (data?.tiebreak_required) {
          this.loadCompetition(categoryId);
          this.success.set('Назначен дополнительный круг. Внесите оценки.');
          return;
        }
  
        this.loadCompetition(categoryId);
        this.loadResults(categoryId);
      },
      error: (err: any) => {
        this.saving.set(false);
        this.handleError(err);
      }
    });
  }

  // ─────────────────────────────
  // Результаты
  // ─────────────────────────────

  loadResults(categoryId: number): void {
    this.service.getResults(
      this.tournamentId,
      categoryId
    ).subscribe({
      next: (data: any) => {
        this.resultsByCategory.update(current => ({
          ...current,
          [categoryId]: data ?? []
        }));
      },
      error: (err: any) => this.handleError(err)
    });
  }

  resultsFor(categoryId: number): any[] {
    return this.resultsByCategory()[categoryId] ?? [];
  }

  // ─────────────────────────────
  // Ошибки
  // ─────────────────────────────

  handleError(err: any): void {
    this.error.set(
      err?.error?.detail
      ?? err?.message
      ?? 'Произошла ошибка'
    );
  }

}