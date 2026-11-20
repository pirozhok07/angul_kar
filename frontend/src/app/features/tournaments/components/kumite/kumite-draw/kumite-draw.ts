import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';

import { KumiteDrawService } from '../kumite-draw.service';

@Component({
  imports: [CommonModule, RouterLink],
  selector: 'app-kumite-draw',
  standalone: true,
  styleUrl: './kumite-draw.scss',
  templateUrl: './kumite-draw.html',
})
export class KumiteDraw implements OnInit {
  private route = inject(ActivatedRoute);
  private service = inject(KumiteDrawService);

  tournamentId = 0;
  categoryId = 0;

  category = signal<any>(null);
  participants = signal<any[]>([]);
  matches = signal<any[]>([]);
  rounds = signal<any[]>([]);
  format = signal('');

  loading = signal(false);
  generating = signal(false);
  saving = signal(false);

  error = signal('');
  success = signal('');

  // Перетаскивание непосредственно в сетке.
  draggedSlot = signal<string | null>(null);

  // Есть несохранённые изменения сетки.
  drawChanged = signal(false);

  participantCount = computed(
    () => this.participants().length
  );

  ngOnInit(): void {
    this.tournamentId = Number(
      this.route.parent?.snapshot.paramMap.get('id')
    );

    this.categoryId = Number(
      this.route.snapshot.paramMap.get('categoryId')
    );

    if (
      !Number.isInteger(this.tournamentId) ||
      this.tournamentId <= 0 ||
      !Number.isInteger(this.categoryId) ||
      this.categoryId <= 0
    ) {
      this.error.set(
        'Не удалось определить турнир или категорию'
      );
      return;
    }

    this.load();
  }

  // ============================================================
  // ЗАГРУЗКА ЖЕРЕБЬЁВКИ
  // ============================================================

  load(): void {
    this.loading.set(true);
    this.error.set('');
    this.success.set('');

    this.service.getAll(
      this.tournamentId,
      this.categoryId
    ).subscribe({
      next: data => {
        this.applyData(data);
        this.drawChanged.set(false);
        this.loading.set(false);
      },
      error: err => {
        this.error.set(
          err.error?.detail ||
          'Не удалось загрузить жеребьёвку'
        );
        this.loading.set(false);
      }
    });
  }

  private applyData(data: any): void {
    this.category.set(data.category ?? null);
    this.format.set(data.format ?? '');

    this.participants.set(
      (data.participants ?? []).map(
        (item: any) => ({ ...item })
      )
    );

    this.matches.set(data.matches ?? []);

    this.rounds.set(
      (data.rounds ?? []).map((round: any) => ({
        ...round,
        matches: (round.matches ?? []).map(
          (match: any) => ({ ...match })
        )
      }))
    );
  }

  // ============================================================
  // API: ГЕНЕРАЦИЯ ЖЕРЕБЬЁВКИ
  // ============================================================

  generate(): void {
    if (this.generating() || this.saving()) return;

    this.generating.set(true);
    this.error.set('');
    this.success.set('');

    this.service.generate(
      this.tournamentId,
      this.categoryId
    ).subscribe({
      next: data => {
        this.applyData(data);
        this.drawChanged.set(false);
        this.generating.set(false);
        this.success.set('Жеребьёвка сформирована');
      },
      error: err => {
        this.error.set(
          err.error?.detail ||
          'Не удалось сформировать жеребьёвку'
        );
        this.generating.set(false);
      }
    });
  }

  // ============================================================
  // ПЕРЕТАСКИВАНИЕ СПОРТСМЕНОВ В СЕТКЕ
  // ============================================================

  onSlotDragStart(event: DragEvent, slot: string): void {
    if (this.saving()) {
      event.preventDefault();
      return;
    }

    this.draggedSlot.set(slot);

    if (event.dataTransfer) {
      event.dataTransfer.setData('text/plain', slot);
      event.dataTransfer.effectAllowed = 'move';
    }
  }

  onSlotDragOver(event: DragEvent): void {
    event.preventDefault();

    if (event.dataTransfer) {
      event.dataTransfer.dropEffect = 'move';
    }
  }

  onSlotDrop(event: DragEvent, targetSlot: string): void {
    event.preventDefault();

    if (this.saving()) return;

    const sourceSlot = this.draggedSlot();
    this.draggedSlot.set(null);

    if (!sourceSlot || sourceSlot === targetSlot) return;

    const [sourceMatchIndex, sourceSide] =
      sourceSlot.split(':');

    const [targetMatchIndex, targetSide] =
      targetSlot.split(':');

    const updatedRounds = this.rounds().map(
      (round: any) => ({
        ...round,
        matches: round.matches.map(
          (match: any) => ({ ...match })
        )
      })
    );

    const firstRound = updatedRounds[0];

    if (!firstRound) return;

    const source = firstRound.matches[
      Number(sourceMatchIndex)
    ];

    const target = firstRound.matches[
      Number(targetMatchIndex)
    ];

    if (!source || !target) return;

    const sourceIdKey =
      sourceSide === '1' ? 'athlete1_id' : 'athlete2_id';

    const sourceNameKey =
      sourceSide === '1' ? 'athlete1' : 'athlete2';

    const targetIdKey =
      targetSide === '1' ? 'athlete1_id' : 'athlete2_id';

    const targetNameKey =
      targetSide === '1' ? 'athlete1' : 'athlete2';

    // Меняем местами ID и отображаемые имена.
    const tempId = source[sourceIdKey];
    const tempName = source[sourceNameKey];

    source[sourceIdKey] = target[targetIdKey];
    source[sourceNameKey] = target[targetNameKey];

    target[targetIdKey] = tempId;
    target[targetNameKey] = tempName;

    // Старые результаты после изменения расстановки
    // больше не действительны.
    for (const round of updatedRounds) {
      for (const match of round.matches) {
        match.winner_athlete_id = null;

        if (match.status === 'completed') {
          match.status = 'pending';
        }
      }
    }

    // Пересчитываем все последующие раунды.
    this.recalculateFollowingRounds(updatedRounds);

    this.rounds.set(updatedRounds);
    this.drawChanged.set(true);

    this.error.set('');
    this.success.set('');
  }

  onSlotDragEnd(): void {
    this.draggedSlot.set(null);
  }

  // ============================================================
  // ЛОКАЛЬНЫЙ ПЕРЕСЧЁТ ПОСЛЕДУЮЩИХ РАУНДОВ
  // ============================================================

  private getAdvancedAthlete(match: any): {
    id: number | null;
    name: string;
    resolved: boolean;
  } {
    if (match.status === 'bye') {
      const id =
        match.athlete1_id ?? match.athlete2_id;

      return {
        id,
        name: id === match.athlete1_id
          ? match.athlete1
          : match.athlete2,
        resolved: true
      };
    }

    if (match.status === 'empty') {
      return {
        id: null,
        name: '—',
        resolved: true
      };
    }

    // При перестановке все результаты сбрасываются.
    // Поэтому завершённых боёв здесь нет.
    return {
      id: null,
      name: 'Ожидает победителя',
      resolved: false
    };
  }

  private recalculateFollowingRounds(rounds: any[]): void {
    for (
      let roundIndex = 1;
      roundIndex < rounds.length;
      roundIndex++
    ) {
      const previousMatches =
        rounds[roundIndex - 1].matches;

      const currentMatches =
        rounds[roundIndex].matches;

      currentMatches.forEach(
        (match: any, index: number) => {
          const firstPrevious =
            previousMatches[index * 2];

          const secondPrevious =
            previousMatches[index * 2 + 1];

          if (!firstPrevious || !secondPrevious) return;

          const first =
            this.getAdvancedAthlete(firstPrevious);

          const second =
            this.getAdvancedAthlete(secondPrevious);

          match.athlete1_id = first.id;
          match.athlete1 = first.name;

          match.athlete2_id = second.id;
          match.athlete2 = second.name;

          match.winner_athlete_id = null;

          if (!first.resolved || !second.resolved) {
            match.status = 'pending';
          } else if (!first.id && !second.id) {
            match.status = 'empty';
          } else if (!first.id || !second.id) {
            match.status = 'bye';
          } else {
            match.status = 'pending';
          }
        }
      );
    }
  }

  // ============================================================
  // API: СОХРАНЕНИЕ ИЗМЕНЁННОЙ СЕТКИ
  // ============================================================

  saveDraw(): void {
    if (
      !this.drawChanged() ||
      this.saving()
    ) {
      return;
    }

    const firstRound = this.rounds()[0];

    if (!firstRound) return;

    const slots: {
      position: number;
      athlete_id: number | null;
    }[] = [];

    firstRound.matches.forEach((match: any) => {
      slots.push({
        position: slots.length + 1,
        athlete_id: match.athlete1_id ?? null
      });

      slots.push({
        position: slots.length + 1,
        athlete_id: match.athlete2_id ?? null
      });
    });

    this.saving.set(true);
    this.error.set('');
    this.success.set('');

    this.service.saveSlots(
      this.tournamentId,
      this.categoryId,
      slots
    ).subscribe({
      next: data => {
        this.applyData(data);
        this.drawChanged.set(false);
        this.saving.set(false);
        this.success.set('Жеребьёвка сохранена');
      },
      error: err => {
        this.error.set(
          err.error?.detail ||
          'Не удалось сохранить жеребьёвку'
        );
        this.saving.set(false);
      }
    });
  }

  // ============================================================
  // API: РЕЗУЛЬТАТЫ БОЁВ
  // ============================================================

  setWinner(match: any, athleteId: number): void {
    if (
      this.drawChanged() ||
      this.saving() ||
      !match.id ||
      match.status === 'bye' ||
      match.status === 'empty' ||
      !match.athlete1_id ||
      !match.athlete2_id
    ) {
      return;
    }

    this.error.set('');
    this.success.set('');

    this.service.setWinner(
      this.tournamentId,
      this.categoryId,
      match.id,
      athleteId
    ).subscribe({
      next: data => {
        this.applyData(data);
        this.success.set('Результат боя сохранён');
      },
      error: err => {
        this.error.set(
          err.error?.detail ||
          'Не удалось сохранить результат боя'
        );
      }
    });
  }

  clearWinner(match: any): void {
    if (
      this.drawChanged() ||
      !match.id ||
      match.status !== 'completed'
    ) {
      return;
    }

    this.service.setWinner(
      this.tournamentId,
      this.categoryId,
      match.id,
      null
    ).subscribe({
      next: data => {
        this.applyData(data);
        this.success.set('Результат боя отменён');
      },
      error: err => {
        this.error.set(
          err.error?.detail ||
          'Не удалось отменить результат'
        );
      }
    });
  }

  // ============================================================
  // ОТОБРАЖЕНИЕ
  // ============================================================

  getAthleteName(athlete: any): string {
    return athlete.name ||
      [
        athlete.last_name,
        athlete.first_name,
        athlete.second_name
      ].filter(Boolean).join(' ');
  }

  roundTitle(round: any): string {
    if (round.name) return round.name;

    const total = this.rounds().length;
    const remaining = total - round.round_number;

    if (remaining === 0) return 'Финал';
    if (remaining === 1) return 'Полуфинал';
    if (remaining === 2) return 'Четвертьфинал';

    return `Круг ${round.round_number}`;
  }

  isWinner(match: any, athleteId: number): boolean {
    return (
      match.status === 'completed' &&
      match.winner_athlete_id === athleteId
    );
  }
}