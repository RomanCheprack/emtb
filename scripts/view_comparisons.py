from models import get_session, Comparison, Bike
import json

def view_comparisons():
    """View all comparisons in the database"""
    session = get_session()
    
    try:
        # Get all comparisons ordered by creation date (newest first)
        comparisons = session.query(Comparison).order_by(Comparison.created_at.desc()).all()
        
        print("=== Comparisons Table ===")
        print(f"Total comparisons: {len(comparisons)}")
        print()
        
        if not comparisons:
            print("No comparisons found in database.")
            return
        
        for i, comp in enumerate(comparisons, 1):
            print(f"=== Comparison #{comp.id} ===")
            print(f"Created: {comp.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Get bike IDs
            bike_ids = comp.get_bike_ids()
            print(f"Bikes compared: {len(bike_ids)}")
            for j, bike_id in enumerate(bike_ids, 1):
                bike = session.query(Bike).filter_by(id=bike_id).first()
                bike_name = f"{bike.firm} {bike.model}" if bike else "Unknown Bike"
                print(f"  {j}. {bike_name} (ID: {bike_id})")
            
            # Get comparison data
            data = comp.get_comparison_data()
            if data:
                print(f"\nIntro: {data.get('intro', 'N/A')[:100]}...")
                print(f"Expert tip: {data.get('expert_tip', 'N/A')[:100]}...")
                
                bikes_data = data.get('bikes', [])
                print(f"Bikes in comparison: {len(bikes_data)}")
                for j, bike_data in enumerate(bikes_data, 1):
                    name = bike_data.get('name', 'Unknown')
                    pros = bike_data.get('pros', [])
                    cons = bike_data.get('cons', [])
                    print(f"  {j}. {name}")
                    print(f"     Pros: {len(pros)} items")
                    print(f"     Cons: {len(cons)} items")
            
            print("-" * 80)
            print()
            
    except Exception as e:
        print(f"Error viewing comparisons: {e}")
    finally:
        session.close()

def view_latest_comparison():
    """View the most recent comparison in detail"""
    session = get_session()
    
    try:
        latest = session.query(Comparison).order_by(Comparison.created_at.desc()).first()
        
        if not latest:
            print("No comparisons found in database.")
            return
        
        print("=== Latest Comparison ===")
        print(f"ID: {latest.id}")
        print(f"Created: {latest.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Get bike IDs
        bike_ids = latest.get_bike_ids()
        print(f"\nBikes compared ({len(bike_ids)}):")
        for i, bike_id in enumerate(bike_ids, 1):
            bike = session.query(Bike).filter_by(id=bike_id).first()
            bike_name = f"{bike.firm} {bike.model}" if bike else "Unknown Bike"
            print(f"  {i}. {bike_name} (ID: {bike_id})")
        
        # Get full comparison data
        data = latest.get_comparison_data()
        if data:
            print(f"\n=== Full Comparison Data ===")
            print(f"Intro: {data.get('intro', 'N/A')}")
            print(f"\nRecommendation: {data.get('recommendation', 'N/A')}")
            print(f"\nExpert tip: {data.get('expert_tip', 'N/A')}")
            
            bikes_data = data.get('bikes', [])
            print(f"\n=== Bike Details ({len(bikes_data)} bikes) ===")
            for i, bike_data in enumerate(bikes_data, 1):
                print(f"\n{i}. {bike_data.get('name', 'Unknown')}")
                print(f"   Best for: {bike_data.get('best_for', 'N/A')}")
                
                pros = bike_data.get('pros', [])
                if pros:
                    print(f"   Pros:")
                    for pro in pros:
                        print(f"     • {pro}")
                
                cons = bike_data.get('cons', [])
                if cons:
                    print(f"   Cons:")
                    for con in cons:
                        print(f"     • {con}")
        
    except Exception as e:
        print(f"Error viewing latest comparison: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    print("Choose an option:")
    print("1. View all comparisons (summary)")
    print("2. View latest comparison (detailed)")
    
    choice = input("Enter your choice (1 or 2): ").strip()
    
    if choice == "1":
        view_comparisons()
    elif choice == "2":
        view_latest_comparison()
    else:
        print("Invalid choice. Showing all comparisons...")
        view_comparisons() 