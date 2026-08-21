# =======================================================
        # 🚀 STRATEGY LOGIC (TREND FOLLOWER -> 2-CIRCLE MODE) 🚀
        # =======================================================
        if state["mode"] == "normal":
            if state["bs_level"] >= 4: 
                state["mode"] = "2-circle"
                # बदल: Level 3 चे जे prediction होते, तेच पुढे L4 आणि L5 साठी टार्गेट राहील
                state["circle_current_target"] = state["bs_pred"] 
                state["circle_count"] = 1
                state["bs_pred"] = state["circle_current_target"]
            else:
                state["bs_pred"] = latest_bs
                
        elif state["mode"] == "2-circle":
            state["circle_count"] += 1
            # L4, L5 (२ वेळा) झाल्यानंतर L6 ला रंग विरुद्ध होईल
            if state["circle_count"] > 2:
                state["circle_current_target"] = "Small" if state["circle_current_target"] == "Big" else "Big"
                state["circle_count"] = 1
            state["bs_pred"] = state["circle_current_target"]
        # =======================================================
