import { ComponentFixture, TestBed } from '@angular/core/testing';
import { KumiteDraw } from './kumite-draw';

describe('KumiteDraw', () => {
  let component: KumiteDraw;
  let fixture: ComponentFixture<KumiteDraw>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [KumiteDraw],
    }).compileComponents();

    fixture = TestBed.createComponent(KumiteDraw);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
