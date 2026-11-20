import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Kata } from './kata';

describe('Kata', () => {
  let component: Kata;
  let fixture: ComponentFixture<Kata>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Kata],
    }).compileComponents();

    fixture = TestBed.createComponent(Kata);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
