import { ComponentFixture, TestBed } from '@angular/core/testing';
import { KataDraw } from './kata-draw';

describe('KataDraw', () => {
  let component: KataDraw;
  let fixture: ComponentFixture<KataDraw>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [KataDraw],
    }).compileComponents();

    fixture = TestBed.createComponent(KataDraw);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
